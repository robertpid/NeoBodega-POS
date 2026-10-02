from pydantic import BaseModel
from datetime import datetime

class MarketAlertBase(BaseModel):
    commodity_name: str
    reason: str
    severity: str = "MEDIUM"

class MarketAlertCreate(MarketAlertBase):
    pass

class MarketAlertResponse(MarketAlertBase):
    id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
