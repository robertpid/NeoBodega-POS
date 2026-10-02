from sqlalchemy import Column, Integer, String, Float, Boolean
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, default=0.0)
    stock = Column(Float, default=0)
    image_local_path = Column(String, nullable=True)
    requires_price_setup = Column(Boolean, default=False)
    is_bulk = Column(Boolean, default=False)
