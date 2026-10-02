import logging
from typing import Any, List
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.models.customer import Customer
from app.models.outbox import OutboxMessage
from app.schemas.outbox import OutboxMessageResponse
from app.services.crm_ml import recommend_cross_sell_product
from app.services.crm_service import generar_mensaje_ia, enviar_whatsapp
from app.api.deps import get_current_admin
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

async def async_ia_generation_worker(cliente_id: int, nombre_cliente: str, producto_sugerido: str):
    """
    Paso 1 (HITL Background Task): Genera el mensaje IA y lo guarda en la bandeja 
    de salida (Outbox) con estado 'pendiente', evitando envíos automatizados ciegos.
    """
    # Creamos una sesión nueva, segura para backgrounds (desligada del thread HTTP)
    db = SessionLocal()
    try:
        contexto_compra = "Cliente recurrente analizado por algoritmo FP-Growth."
        mensaje = await generar_mensaje_ia(nombre_cliente, producto_sugerido, contexto_compra)
        
        # INSERT en mensajes_outbox
        nuevo_mensaje = OutboxMessage(
            cliente_id=cliente_id,
            mensaje_generado=mensaje,
            estado="pendiente"
        )
        db.add(nuevo_mensaje)
        db.commit()
        logger.info(f"Mensaje para cliente ID {cliente_id} generado por IA y enviado al Outbox (Pendiente).")
    except Exception as e:
        logger.error(f"Fallo en BackgroundTask de IA: {str(e)}")
    finally:
        db.close()

@router.post("/send-recommendation/{customer_id}")
async def trigger_crm_recommendation(
    customer_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
) -> Any:
    """
    (Refactorizado para HITL) Calcula recomendación ML y encola generación de texto.
    """
    logger.info(f"Admin '{current_user.username}' solicitó draft de campaña para cliente {customer_id}")
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="El cliente no existe en base de datos.")
        
    producto_sugerido = recommend_cross_sell_product(db, customer_id)
    if not producto_sugerido:
        raise HTTPException(status_code=400, detail="Historial insuficiente para recomendar venta cruzada.")
        
    # Encolar la generación de texto sin bloquear. El envío a WhatsApp YA NO es directo.
    background_tasks.add_task(async_ia_generation_worker, customer.id, customer.name, producto_sugerido)
    
    return {
        "status": "Draft Encolado", 
        "message": "Recomendación calculada exitosamente. La IA redactará el mensaje en segundo plano y quedará pendiente de aprobación.",
        "producto_recomendado": producto_sugerido
    }

@router.get("/mensajes/pendientes", response_model=List[OutboxMessageResponse])
def get_pending_messages(db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """
    Paso 2 (HITL): Obtiene todos los mensajes redactados por la IA esperando revisión humana.
    Ruta final (por el prefix de main.py): /api/v1/crm/mensajes/pendientes
    """
    logger.info(f"Admin '{current_user.username}' revisando bandeja de salida de CRM.")
    mensajes = db.query(OutboxMessage).filter(OutboxMessage.estado == "pendiente").all()
    return mensajes

@router.post("/mensajes/{mensaje_id}/aprobar")
@limiter.limit("5/minute")
async def approve_and_send_message(
    request: Request,
    mensaje_id: int, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_admin)
):
    """
    Paso 3 (HITL): Un humano aprueba la redacción y se despacha a la Cloud API de WhatsApp.
    Ruta final: /api/v1/crm/mensajes/{id}/aprobar
    """
    logger.info(f"Admin '{current_user.username}' aprobando envío del mensaje #{mensaje_id}.")
    
    mensaje_outbox = db.query(OutboxMessage).filter(OutboxMessage.id == mensaje_id).first()
    if not mensaje_outbox:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
        
    if mensaje_outbox.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Invalido: El mensaje se encuentra '{mensaje_outbox.estado}'.")
        
    cliente = db.query(Customer).filter(Customer.id == mensaje_outbox.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=400, detail="El cliente asociado al mensaje fue borrado o no existe.")

    # Ejecutar la llamada HTTP a WhatsApp
    exito = await enviar_whatsapp(cliente.phone_number, mensaje_outbox.mensaje_generado)
    
    if exito:
        mensaje_outbox.estado = "enviado"
        db.commit()
        logger.info(f"Mensaje {mensaje_id} aprobado y enviado a WhatsApp Business con éxito.")
        return {"status": "enviado", "message": "Mensaje despachado correctamente a la red de Meta."}
    else:
        mensaje_outbox.estado = "error"
        db.commit()
        logger.error(f"El mensaje {mensaje_id} falló al contactar WhatsApp. Marcado como 'error'.")
        raise HTTPException(status_code=502, detail="Error de comunicación (Timeout o Caída) con la Cloud API de Meta.")
