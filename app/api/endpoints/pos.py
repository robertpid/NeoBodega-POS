import logging
from datetime import date
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.sale import Sale, PaymentMethod
from app.api.deps import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cierre-caja", response_model=Dict[str, float])
def cierre_de_caja(db: Session = Depends(get_db), current_user = Depends(get_current_admin)) -> Any:
    """
    Agrupa los ingresos del día actual por método de pago.
    Protección Activa: Solo permite acceso al Administrador.
    """
    logger.info(f"Administrador '{current_user.username}' solicitó el Cierre de Caja.")
    
    hoy = date.today()
    # SQL Group By para eficiencia (Evita iteraciones iterrows/itertuples ineficientes)
    resultados = (
        db.query(Sale.payment_method, func.sum(Sale.total_amount))
        .filter(func.date(Sale.created_at) == str(hoy))
        .group_by(Sale.payment_method)
        .all()
    )
    
    # Diccionario inicializado con todos los métodos (incluyendo los que facturaron cero)
    resumen = {method.value: 0.0 for method in PaymentMethod}
    for metodo, total in resultados:
        if metodo:
            resumen[metodo.value] = round(total, 2)
            
    resumen["Total_Dia"] = round(sum(resumen.values()), 2)
    return resumen
