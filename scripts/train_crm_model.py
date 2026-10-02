import os
import sys
import logging
import pickle
import pandas as pd
from sqlalchemy import create_engine
from mlxtend.frequent_patterns import fpgrowth, association_rules

# Añadimos la raíz del proyecto para importar módulos absolutos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ML-BATCH: %(message)s")
logger = logging.getLogger(__name__)

# Ubicación donde el modelo guardará las reglas para lectura de API
RULES_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "core", "crm_rules.pkl")

def extract_sales_data(engine) -> pd.DataFrame:
    """Extrae el historial de ventas uniendo tickets y productos (Data Engineering)."""
    logger.info("Extrayendo historial de ventas de SQLite...")
    query = """
        SELECT s.id as transaction_id, p.name as product_name
        FROM sales s
        JOIN sale_items si ON s.id = si.sale_id
        JOIN products p ON si.product_id = p.id
    """
    df = pd.read_sql_query(query, engine)
    return df

def preprocess_for_market_basket(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma los datos al formato transaccional (One-Hot Encoding) usando Pandas puro."""
    logger.info("Preprocesando datos a formato transaccional...")
    # Agrupar por ticket y hacer pivot
    basket = (df.groupby(['transaction_id', 'product_name'])['product_name']
              .count().unstack().reset_index().fillna(0)
              .set_index('transaction_id'))
    
    # Binarizar (1 si compró, 0 si no)
    def encode_units(x):
        if x <= 0: return False
        if x >= 1: return True
    
    basket_sets = basket.map(encode_units)
    return basket_sets

def train_association_rules(basket_sets: pd.DataFrame):
    """Ejecuta el algoritmo FP-Growth (más eficiente que Apriori) y genera reglas."""
    logger.info("Entrenando modelo FP-Growth...")
    # Soporte mínimo: el item debe aparecer en al menos 1% de las ventas
    frequent_itemsets = fpgrowth(basket_sets, min_support=0.01, use_colnames=True)
    
    if frequent_itemsets.empty:
        logger.warning("Datos insuficientes para encontrar itemsets frecuentes.")
        return None

    # Reglas con 'lift' > 1 indican que A y B se compran juntos más de lo esperado
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
    logger.info(f"Se generaron {len(rules)} reglas de asociación fuertes.")
    return rules

def save_rules(rules: pd.DataFrame):
    """Guarda las reglas pre-calculadas en un binario para latencia cero en la API."""
    logger.info(f"Serializando modelo en {RULES_FILE_PATH}")
    with open(RULES_FILE_PATH, 'wb') as f:
        pickle.dump(rules, f)

def run_ml_pipeline():
    """Pipeline completo de reentrenamiento. Ideal para ejecutarse de madrugada (Cron/Batch)."""
    logger.info("Iniciando pipeline de Machine Learning (Market Basket Analysis)...")
    engine = create_engine(DATABASE_URL)
    df = extract_sales_data(engine)
    
    if df.empty or len(df['transaction_id'].unique()) < 5:
        logger.warning("No hay suficientes transacciones (min 5) para entrenar el modelo.")
        return

    basket_sets = preprocess_for_market_basket(df)
    rules = train_association_rules(basket_sets)
    
    if rules is not None and not rules.empty:
        save_rules(rules)
        logger.info("Pipeline finalizado. Reglas desplegadas y listas para FastAPI.")

if __name__ == "__main__":
    run_ml_pipeline()
