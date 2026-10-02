from pydantic import BaseModel
from datetime import datetime

class OutboxMessageResponse(BaseModel):
    id: int
    cliente_id: int
    mensaje_generado: str
    estado: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True
