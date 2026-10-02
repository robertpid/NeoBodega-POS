from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin
from app.core.security import get_password_hash
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    class Config:
        from_attributes = True

@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Lista todos los usuarios. Requiere rol Admin."""
    return db.query(User).all()

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Crea un usuario nuevo. Requiere rol Admin."""
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    new_user = User(
        username=user_in.username, 
        hashed_password=get_password_hash(user_in.password), 
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    """Elimina un usuario. Requiere rol Admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Operación bloqueada: No puedes eliminar al Super Administrador")
    
    db.delete(user)
    db.commit()
    return {"status": "ok", "message": "Usuario eliminado correctamente"}
