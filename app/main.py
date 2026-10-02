import logging
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.database import Base, engine
from app.api.endpoints import inventory, market

logger = logging.getLogger(__name__)

# Crear tablas en SQLite local
logger.info("Inicializando la base de datos...")
Base.metadata.create_all(bind=engine)

# Iniciar FastAPI y middlewares
app = FastAPI(title="Ecosistema Inteligente POS API")

# --- SEGURIDAD DEVSECOPS: Rate Limiting ---
from app.core.rate_limit import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- SEGURIDAD DEVSECOPS: CORS (Cross-Origin Resource Sharing) ---
origins = [
    "http://localhost:3000",  # Frontend típico React / Next.js
    "http://localhost:5173",  # Frontend típico Vite
    "http://localhost:8080",  # Frontend típico Vue.js
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rutas operacionales
from app.api.endpoints import inventory, market, pos, crm, users
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.core.database import get_db
from sqlalchemy.orm import Session
from datetime import timedelta

# Endpoint Login (JWT Token) - Protegido contra ataques de Fuerza Bruta
@app.post("/token")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrecta")
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=480))
    return {"access_token": access_token, "token_type": "bearer"}

# Incluir routers modulares
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Intelligence"])
app.include_router(pos.router, prefix="/api/v1/pos", tags=["Caja & Finanzas"])
app.include_router(crm.router, prefix="/api/v1/crm", tags=["Fidelización"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])

@app.get("/")
def read_root() -> dict:
    return {"message": "Bienvenido al Ecosistema Inteligente POS"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando aplicación FastAPI (Standalone)")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
