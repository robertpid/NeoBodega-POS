from typing import Optional
from pydantic import BaseModel

class BarcodeRequest(BaseModel):
    barcode: str

class ProductBase(BaseModel):
    barcode: str
    name: str
    price: float
    stock: float = 0
    image_local_path: Optional[str] = None
    requires_price_setup: bool = False
    is_bulk: bool = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None
    name: Optional[str] = None
    barcode: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    status_msg: Optional[str] = None

    class Config:
        from_attributes = True
