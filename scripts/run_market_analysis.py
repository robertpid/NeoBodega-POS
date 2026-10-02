import asyncio
import logging
import sys
import os

# Añadimos el root del proyecto al path para importar como módulo absoluto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.market_ai import fetch_economic_news, analyze_headlines_with_ia
from app.crud.alert_crud import create_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] SCRIPTS: %(message)s")
logger = logging.getLogger(__name__)

async def run_daily_analysis():
    """
    Script diseñado para ser ejecutado diariamente (ej. vía CRON).
    Descarga RSS, analiza con IA y guarda las Alertas en la BD.
    """
    logger.info("Iniciando trabajo diario de Inteligencia de Mercado...")
    
    # 1. Leer RSS de forma robusta
    headlines = fetch_economic_news()
    if not headlines:
        logger.warning("No se obtuvieron titulares para analizar hoy.")
        return

    # 2. Análisis del LLM
    alerts_to_create = await analyze_headlines_with_ia(headlines)
    
    # 3. Guardar en SQLite (Base de datos local)
    if alerts_to_create:
        db = SessionLocal()
        try:
            for alert in alerts_to_create:
                create_alert(db, alert)
            logger.info(f"Éxito: Se generaron {len(alerts_to_create)} alertas tempranas.")
        except Exception as e:
            logger.error(f"Error al guardar alertas en BD: {str(e)}")
        finally:
            db.close()
    else:
        logger.info("El análisis no detectó riesgos inminentes de inflación para hoy.")

if __name__ == "__main__":
    asyncio.run(run_daily_analysis())
