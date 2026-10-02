import logging

logger = logging.getLogger(__name__)

def download_product_image(image_url: str, barcode: str) -> str:
    """
    3. Automatización en cascada: Descarga la imagen oficial del producto.
    """
    logger.info(f"Descargando imagen desde {image_url} para {barcode}")
    # Simulación de descarga y guardado de archivo
    local_path = f"/static/img/products/{barcode}.jpg"
    return local_path
