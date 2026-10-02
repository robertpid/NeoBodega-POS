import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)

def get_product_by_barcode(db: Session, barcode: str) -> Optional[Product]:
    """1. ¿Existe en la base de datos local?"""
    logger.info(f"Buscando producto en BD local: {barcode}")
    return db.query(Product).filter(Product.barcode == barcode).first()

def create_product(db: Session, product_data: ProductCreate) -> Product:
    """4. Guardar datos y requerir establecimiento de precio."""
    logger.info(f"Insertando nuevo producto en BD: {product_data.barcode}")
    db_product = Product(**product_data.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        return None
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product
