from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class OutboxMessage(Base):
    __tablename__ = "mensajes_outbox"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    mensaje_generado = Column(String, nullable=False)
    estado = Column(String, default="pendiente", index=True) # Estados: 'pendiente', 'enviado', 'error'
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
