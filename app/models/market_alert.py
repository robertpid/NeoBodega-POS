from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class MarketAlert(Base):
    __tablename__ = "market_alerts"

    id = Column(Integer, primary_key=True, index=True)
    commodity_name = Column(String, index=True, nullable=False)
    reason = Column(String, nullable=False)
    severity = Column(String, default="MEDIUM") # HIGH, MEDIUM, LOW
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
