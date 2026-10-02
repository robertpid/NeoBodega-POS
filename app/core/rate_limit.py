from slowapi import Limiter
from slowapi.util import get_remote_address

# Inicialización centralizada del Rate Limiter
# Utiliza la IP del cliente (get_remote_address) para determinar los umbrales de acceso.
limiter = Limiter(key_func=get_remote_address)
