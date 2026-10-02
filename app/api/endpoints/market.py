import logging
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.market_alert import MarketAlertResponse
from app.crud.alert_crud import get_unread_alerts, mark_alert_as_read

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/alerts/active", response_model=List[MarketAlertResponse], status_code=status.HTTP_200_OK)
def get_active_alerts(db: Session = Depends(get_db)) -> Any:
    """
    Obtiene todas las Alertas Tempranas de Mercado que no han sido leídas por la bodega.
    (Operación optimizada para consultar en la caja del POS).
    """
    logger.info("Pantalla POS consultando alertas activas de mercado.")
    return get_unread_alerts(db)

@router.put("/alerts/{alert_id}/read", response_model=MarketAlertResponse)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)) -> Any:
    """
    Marca una alerta como leída una vez que el bodeguero la vio en pantalla.
    """
    alert = mark_alert_as_read(db, alert_id)
    if not alert:
        logger.warning(f"Intento de marcar como leída una alerta inexistente: {alert_id}")
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert
