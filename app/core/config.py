import logging

# Configuración central del logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

DATABASE_URL = "sqlite:///./pos_mvp.db"
