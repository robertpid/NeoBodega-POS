import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def consult_online_api(barcode: str) -> Optional[dict]:
    """
    2. Consultar API de productos en línea.
    """
    logger.info(f"Consultando API externa para barcode: {barcode}")
    # Simulación de respuesta de API externa
    if barcode == "770123456789":
        return {
            "barcode": barcode,
            "name": "Arroz Costeño",
            "image_url": "http://api.com/arroz.jpg"
        }
    return None
