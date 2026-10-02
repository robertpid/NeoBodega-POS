import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import timedelta
from sqlalchemy import create_engine
import xgboost as xgb

# Añadimos la raíz del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import DATABASE_URL
from app.core.database import SessionLocal
from app.models.product import Product

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] INV-OPT: %(message)s")
logger = logging.getLogger(__name__)

# Ruta de exportación del reporte JSON (Desacoplado de la API)
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "restock_suggestions.json")

def extract_daily_sales(engine) -> pd.DataFrame:
    """Extrae y agrupa el historial de ventas con frecuencia diaria."""
    logger.info("Extrayendo ventas históricas de SQLite...")
    query = """
        SELECT date(s.created_at) as fecha, si.product_id, SUM(si.quantity) as cantidad_vendida
        FROM sales s
        JOIN sale_items si ON s.id = si.sale_id
        GROUP BY date(s.created_at), si.product_id
    """
    df = pd.read_sql_query(query, engine)
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
    return df

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Crea features temporales básicas para ayudar al árbol de decisión de XGBoost."""
    df['day_of_week'] = df['fecha'].dt.dayofweek
    df['day_of_month'] = df['fecha'].dt.day
    df['month'] = df['fecha'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    return df

def predict_demand_xgboost(df_product: pd.DataFrame) -> dict:
    """
    Modelo de Time Series (XGBoost).
    Predice la demanda de un producto para los siguientes 7 y 14 días.
    """
    # 1. Uniformizar la serie de tiempo (Rellenar días sin ventas con 0)
    min_date = df_product['fecha'].min()
    max_date = df_product['fecha'].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    df_product = df_product.set_index('fecha').reindex(all_dates, fill_value=0).rename_axis('fecha').reset_index()
    
    # 2. Generar Features
    df_product = feature_engineering(df_product)
    
    X = df_product[['day_of_week', 'day_of_month', 'month', 'is_weekend']]
    y = df_product['cantidad_vendida']
    
    # 3. Entrenamiento (XGBRegressor es ideal para tabular series y requiere poco tunning base)
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=3)
    model.fit(X, y)
    
    # 4. Inferencia: Proyectar próximos 14 días
    future_dates = pd.date_range(start=max_date + timedelta(days=1), periods=14, freq='D')
    future_df = pd.DataFrame({'fecha': future_dates})
    future_df = feature_engineering(future_df)
    
    X_future = future_df[['day_of_week', 'day_of_month', 'month', 'is_weekend']]
    predictions = model.predict(X_future)
    
    # Las predicciones de demanda no pueden ser negativas
    predictions = np.maximum(predictions, 0)
    
    return {
        "pred_7_days": round(sum(predictions[:7]), 2),
        "pred_14_days": round(sum(predictions), 2)
    }

def calculate_min_max_stock(df_product: pd.DataFrame) -> dict:
    """
    Manejo de Cold Start: Fórmula estadística simple de Min-Max 
    cuando no hay suficientes datos históricos (< 30 días) para entrenar ML.
    """
    avg_daily_sales = df_product['cantidad_vendida'].mean()
    # Proyección lineal simple
    return {
        "pred_7_days": round(avg_daily_sales * 7, 2),
        "pred_14_days": round(avg_daily_sales * 14, 2)
    }

def evaluate_restock(product: Product, predictions: dict) -> dict:
    """
    Lógica de Reabastecimiento (Punto de Reorden).
    Compara Stock vs Demanda Esperada + 10% Stock de Seguridad.
    """
    current_stock = product.stock
    demand_7d = predictions["pred_7_days"]
    
    # Stock de Seguridad = 10% de la demanda proyectada en 7 días
    safety_stock = demand_7d * 0.10
    reorder_point = demand_7d + safety_stock
    
    # Si estamos por debajo de lo necesario para sobrevivir los próximos 7 días con holgura:
    if current_stock < reorder_point:
        # Sugerimos comprar suficiente mercancía para cubrir 14 días + stock de seguridad
        suggested_qty = round(predictions["pred_14_days"] + safety_stock - current_stock)
        suggested_qty = max(1, suggested_qty) # Garantizar que compre al menos 1 unidad
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "barcode": product.barcode,
            "current_stock": current_stock,
            "predicted_demand_7d": demand_7d,
            "reorder_point": round(reorder_point, 2),
            "suggested_purchase_qty": suggested_qty,
            "action": "RESTOCK_NEEDED"
        }
    return None

def run_inventory_optimization():
    """
    Orquestador del Pipeline. Desacoplado para ejecutarse vía Cron en la madrugada.
    """
    logger.info("Iniciando módulo de Optimización de Inventario Batch...")
    engine = create_engine(DATABASE_URL)
    df_sales = extract_daily_sales(engine)
    
    if df_sales.empty:
        logger.warning("Base de datos sin ventas históricas. Abortando optimización.")
        return

    db = SessionLocal()
    suggestions = []

    try:
        products = db.query(Product).all()
        for prod in products:
            df_prod = df_sales[df_sales['product_id'] == prod.id].copy()
            
            if df_prod.empty:
                continue
                
            days_history = (df_prod['fecha'].max() - df_prod['fecha'].min()).days + 1
            
            # --- EVALUACIÓN DE COLD START ---
            if days_history < 30:
                logger.info(f"[{prod.name}] Cold Start ({days_history} días de data). Usando heurística Min-Max.")
                predictions = calculate_min_max_stock(df_prod)
            else:
                logger.info(f"[{prod.name}] Data suficiente ({days_history} días). Entrenando modelo XGBoost...")
                predictions = predict_demand_xgboost(df_prod)
                
            # --- GENERACIÓN DE SUGERENCIAS ---
            restock_alert = evaluate_restock(prod, predictions)
            if restock_alert:
                suggestions.append(restock_alert)
                
        # --- SALIDA ESTRUCTURADA ---
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Optimización completada. {len(suggestions)} productos requieren abastecimiento.")
        logger.info(f"Reporte de requerimientos exportado a: {REPORT_PATH}")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_inventory_optimization()
