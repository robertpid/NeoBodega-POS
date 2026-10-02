import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.market_alert import MarketAlert
from app.schemas.market_alert import MarketAlertCreate

logger = logging.getLogger(__name__)

def create_alert(db: Session, alert_data: MarketAlertCreate) -> MarketAlert:
    logger.info(f"Guardando nueva alerta de mercado para: {alert_data.commodity_name}")
    db_alert = MarketAlert(**alert_data.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_unread_alerts(db: Session) -> List[MarketAlert]:
    logger.info("Recuperando alertas no leídas de la base de datos")
    return db.query(MarketAlert).filter(MarketAlert.is_read == False).all()

def mark_alert_as_read(db: Session, alert_id: int) -> Optional[MarketAlert]:
    logger.info(f"Intentando marcar la alerta {alert_id} como leída")
    alert = db.query(MarketAlert).filter(MarketAlert.id == alert_id).first()
    if alert:
        alert.is_read = True
        db.commit()
        db.refresh(alert)
        logger.info(f"Alerta {alert_id} marcada como leída exitosamente")
    return alert
