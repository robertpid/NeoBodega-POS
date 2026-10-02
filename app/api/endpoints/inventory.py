import logging
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import BarcodeRequest, ProductResponse, ProductCreate, ProductUpdate
from app.crud.product_crud import get_product_by_barcode, create_product, update_product
from app.services.external_api import consult_online_api
from app.services.image_sync import download_product_image
from app.api.deps import get_current_admin
from app.models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
def get_inventory(db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Obtiene todo el inventario de la bodega."""
    return db.query(Product).all()

@router.post("/", response_model=ProductResponse)
def add_product_manual(product_in: ProductCreate, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Agrega un producto manualmente al inventario."""
    existing = get_product_by_barcode(db, product_in.barcode)
    if existing:
        raise HTTPException(status_code=400, detail="El producto ya existe.")
    return create_product(db, product_in)

@router.put("/{product_id}", response_model=ProductResponse)
def update_inventory_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Actualiza precio y stock de un producto."""
    updated = update_product(db, product_id, product_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return updated

@router.post("/scan", response_model=ProductResponse)
async def scan_product(request: BarcodeRequest, db: Session = Depends(get_db), current_user = Depends(get_current_admin)) -> Any:
    """
    INICIO: Escaneo de Código de Barras
    """
    barcode = request.barcode
    logger.info(f"Inicio de escaneo para: {barcode}")
    
    try:
        # 1. ¿Existe en la base de datos local?
        local_product = get_product_by_barcode(db, barcode)
        if local_product:
            # SI -> FIN: Cargar datos instantáneamente
            logger.info(f"[{barcode}] Encontrado localmente.")
            response = ProductResponse.model_validate(local_product)
            response.status_msg = "Cargado instantáneamente"
            return response
            
        # NO -> 2. Consultar API de productos en línea
        logger.info(f"[{barcode}] No encontrado localmente. Consultando APIs...")
        external_data = await consult_online_api(barcode)
        
        # ¿Se encontraron datos externamente?
        if external_data:
            # SI -> 3. Automatización en cascada: Descargar imagen + Insertar en BD
            logger.info(f"[{barcode}] Hallado externamente. Iniciando automatización en cascada.")
            img_local_path = download_product_image(external_data["image_url"], barcode)
            
            # 4. Guardar datos y requerir establecimiento de precio
            product_in = ProductCreate(
                barcode=external_data["barcode"],
                name=external_data["name"],
                price=0.0,
                stock=0,
                image_local_path=img_local_path,
                requires_price_setup=True
            )
            new_product = create_product(db, product_in)
            
            # FIN: Cargar nuevos datos (requiere precio)
            response = ProductResponse.model_validate(new_product)
            response.status_msg = "Cargar nuevos datos (requiere precio)"
            return response
            
        else:
            # NO -> FIN: Notificar "Requiere registro manual"
            logger.warning(f"[{barcode}] Datos no disponibles. Requiere registro manual.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requiere registro manual"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando {barcode}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando el inventario."
        )
