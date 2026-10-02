import logging
import feedparser
from typing import List
from app.schemas.market_alert import MarketAlertCreate

logger = logging.getLogger(__name__)

# URL RSS de ejemplo (Podría ser configurado en config.py)
RSS_URL = "http://feeds.bbci.co.uk/news/business/rss.xml"

def fetch_economic_news() -> List[str]:
    """
    Descarga noticias de forma robusta usando feedparser.
    Evita la fragilidad del web scraping al consumir XML estándar.
    """
    logger.info(f"Leyendo RSS Feed desde: {RSS_URL}")
    try:
        feed = feedparser.parse(RSS_URL)
        # Extraemos los primeros 10 titulares de impacto
        headlines = [entry.title for entry in feed.entries[:10]]
        logger.info(f"Se extrajeron {len(headlines)} titulares exitosamente.")
        return headlines
    except Exception as e:
        logger.error(f"Error parseando el feed RSS: {str(e)}")
        return []

async def analyze_headlines_with_ia(headlines: List[str]) -> List[MarketAlertCreate]:
    """
    Simulación del motor de Inteligencia Artificial.
    Toma titulares, evalúa patrones de inflación y genera alertas estructuradas.
    """
    logger.info("Procesando titulares a través del Módulo de IA...")
    alerts = []
    
    # En producción aquí se integraría google.generativeai (Gemini)
    for headline in headlines:
        headline_lower = headline.lower()
        if "wheat" in headline_lower or "trigo" in headline_lower or "drought" in headline_lower:
            alerts.append(MarketAlertCreate(
                commodity_name="Harina / Trigo",
                reason=f"Impacto detectado por noticia: {headline}",
                severity="HIGH"
            ))
        elif "oil" in headline_lower or "petróleo" in headline_lower:
            alerts.append(MarketAlertCreate(
                commodity_name="Transporte / Fletes",
                reason=f"Alza en mercado internacional: {headline}",
                severity="HIGH"
            ))
            
    return alerts
