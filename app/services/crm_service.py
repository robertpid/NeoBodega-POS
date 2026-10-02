import os
import logging
import httpx
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Cargar variables de entorno de forma segura (dotenv)
load_dotenv()

# Configuración corporativa del Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] CRM-BOT: %(message)s")
logger = logging.getLogger(__name__)

# Leer variables de configuración sin hardcodear (Seguridad)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Inicialización de la librería oficial de Google Generative AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY no se encontró en el archivo .env")

async def generar_mensaje_ia(nombre_cliente: str, producto_sugerido: str, contexto_compra: str) -> str:
    """
    Motor NLP: Usa IA para redactar un mensaje ultra-personalizado.
    Asíncrono para poder procesar a miles de clientes en batch sin bloquear el hilo principal.
    """
    logger.info(f"Generando mensaje IA para {nombre_cliente} sugiriendo '{producto_sugerido}'...")
    
    if not GEMINI_API_KEY:
        logger.error("Imposible llamar a la IA: API Key ausente.")
        return f"¡Hola {nombre_cliente}! Tenemos en stock {producto_sugerido}. ¡Te esperamos!"

    # Prompt Engineering: Definimos la personalidad, la brevedad y el contexto.
    prompt = (
        f"Actúa como el dueño amable de una bodega de barrio en Latinoamérica. "
        f"Escribe un mensaje de WhatsApp corto (máximo 40 palabras) para tu cliente frecuente llamado {nombre_cliente}. "
        f"Contexto de su compra: '{contexto_compra}'. "
        f"Sugiérele sutilmente que en su próxima visita aproveche para llevar '{producto_sugerido}'. "
        f"Sé cálido, humano, usa un par de emojis, y NO menciones que es un sistema o algoritmo recomendándolo."
    )

    try:
        # Utilizamos el modelo gemini-1.5-flash (Ideal por ser rápido y de bajo costo para NLP ligero)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Llamada asíncrona a la API externa
        response = await model.generate_content_async(prompt)
        mensaje_final = response.text.strip()
        
        logger.info("Mensaje redactado exitosamente por Gemini AI.")
        return mensaje_final
        
    except Exception as e:
        logger.error(f"Fallo conectando con Gemini API: {str(e)}")
        # Resiliencia: Fallback determinista si los servidores de Google se caen.
        return f"¡Hola {nombre_cliente}! Hoy tenemos excelente precio en {producto_sugerido}, te esperamos en la bodega vecina."

async def enviar_whatsapp(numero: str, mensaje: str) -> bool:
    """
    Capa de Mensajería: Realiza el POST HTTP a la infraestructura Cloud API de Meta.
    Maneja timeouts y evita interrupciones en la cola de procesamiento.
    """
    logger.info(f"Encolando envío de WhatsApp al número: {numero}")
    
    if not WHATSAPP_API_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("Envío abortado: Credenciales de WhatsApp Business incompletas en el .env")
        return False

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    # Bloque try/except exhaustivo para resiliencia de red (Data Engineering Best Practices)
    try:
        # httpx asíncrono previene el bloqueo del Thread en caso de alta latencia
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status() # Lanza excepción automáticamente en errores 4xx o 5xx
            
            logger.info("Notificación entregada exitosamente a la Meta Cloud API.")
            return True
            
    except httpx.ReadTimeout:
        logger.error("Timeout: Servidores de Meta no respondieron a tiempo.")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Meta API devolvió un error de estado {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        logger.error(f"Falla de red (DNS o caída de internet) en el host: {exc}")
    except Exception as e:
        logger.error(f"Fallo genérico crítico durante envío a WhatsApp: {str(e)}")
        
    return False

# --- Bloque de Prueba Unitaria para Desarrollo ---
if __name__ == "__main__":
    import asyncio
    
    async def run_test():
        logger.info("--- Iniciando Simulación Aislada del Módulo CRM ---")
        nombre = "Doña María"
        prod = "Saco de Arroz Costeño 5kg"
        contexto = "Compra pan diario, hace 3 semanas llevó arroz y según el ML ya debería estar por terminársele."
        
        mensaje = await generar_mensaje_ia(nombre, prod, contexto)
        print(f"\n[TEXTO GENERADO]:\n{mensaje}\n")
        
        # En producción descomentar para envío real:
        # await enviar_whatsapp("51999123456", mensaje)
        
    asyncio.run(run_test())
