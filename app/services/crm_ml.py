import os
import pickle
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.sale import Sale, SaleItem
from app.models.product import Product

logger = logging.getLogger(__name__)

RULES_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", "crm_rules.pkl")

# Cacheamos las reglas en RAM (Memoria dinámica). 
# FastAPI leerá esto de inmediato sin recargar el modelo.
_cached_rules = None

def load_rules():
    """Carga silenciosa del modelo pre-entrenado (Latencia Cero)"""
    global _cached_rules
    if _cached_rules is None:
        if os.path.exists(RULES_FILE_PATH):
            logger.info("Cargando reglas de Market Basket Analysis en memoria (RAM)...")
            with open(RULES_FILE_PATH, 'rb') as f:
                _cached_rules = pickle.load(f)
        else:
            logger.warning("Archivo de reglas no existe. Falta ejecutar el script de entrenamiento batch.")
            _cached_rules = "EMPTY"
    return _cached_rules

def get_last_purchase_items(db: Session, customer_id: int) -> List[str]:
    """Recupera los productos del último ticket del cliente."""
    last_sale = (db.query(Sale)
                 .filter(Sale.customer_id == customer_id)
                 .order_by(Sale.created_at.desc())
                 .first())
    if not last_sale:
        return []
    
    product_names = []
    # Join manual simple (en producción usaría joinedload de SQLAlchemy)
    for item in last_sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product_names.append(product.name)
    return product_names

def recommend_cross_sell_product(db: Session, customer_id: int) -> Optional[str]:
    """
    Función de Inferencia: 
    Analiza la última compra y devuelve el producto con mayor probabilidad estadística (lift).
    Al usar caché en RAM y DataFrames preprocesados, esta función bloquea la API menos de 2ms.
    """
    rules = load_rules()
    if rules is None or (isinstance(rules, str) and rules == "EMPTY"):
        return None

    last_items = get_last_purchase_items(db, customer_id)
    if not last_items:
        logger.info(f"El cliente {customer_id} no tiene compras previas.")
        return None

    best_recommendation = None
    highest_lift = 0.0

    # Motor de recomendación: Buscar el Consecuente más fuerte dado el Antecedente
    for index, row in rules.iterrows():
        antecedents = set(row['antecedents'])
        consequents = set(row['consequents'])
        
        # Si la última compra incluye todos los items de un antecedente de la regla
        if antecedents.issubset(set(last_items)):
            # Evitar recomendar algo que justo acaba de llevar
            recommendation_candidates = consequents - set(last_items)
            
            if recommendation_candidates and row['lift'] > highest_lift:
                highest_lift = row['lift']
                # Extraemos el primer producto candidato del set
                best_recommendation = list(recommendation_candidates)[0]
                
    if best_recommendation:
        logger.info(f"Recomendación CRM (Cliente {customer_id}): '{best_recommendation}' (Confianza Lift: {highest_lift:.2f})")
    else:
        logger.info(f"No hay correlación fuerte para recomendar al cliente {customer_id} basados en su último ticket.")

    return best_recommendation
