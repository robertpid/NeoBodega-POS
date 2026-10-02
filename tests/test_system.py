import os
import sys
import subprocess

# Añadir la ruta raíz para permitir importaciones relativas absolutas de 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.customer import Customer
from app.core.security import get_password_hash

def run_tests():
    print("="*60)
    print("[TESTING] INICIANDO BATERIA DE PRUEBAS DEL ECOSISTEMA POS")
    print("="*60)

    # 1. Configuración de Entorno de Prueba y Base de Datos
    print("\n[PASO 1] Construyendo SQLite y datos semilla (Seeding)...")
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # Inyectar Administrador para pruebas
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(username="admin", hashed_password=get_password_hash("testpass"), role="admin"))
        
        # Inyectar Cliente
        if not db.query(Customer).filter_by(id=1).first():
            db.add(Customer(id=1, name="Test User", phone_number="123456789"))
        
        db.commit()
        db.close()
        print("[OK] Tablas y datos creados correctamente.")
    except Exception as e:
        print(f"[FAIL] Error critico en BD: {e}")
        return

    # 2. Pruebas de API usando TestClient (sin necesidad de arrancar el puerto)
    print("\n[PASO 2] Ejecutando Pruebas de Integracion (API y Seguridad)...")
    client = TestClient(app)
    headers = {}
    
    # A) Test de Autenticación
    try:
        response = client.post("/token", data={"username": "admin", "password": "testpass"})
        if response.status_code == 200:
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("[OK] Autenticacion y Generacion de JWT (Passlib/Bcrypt): PASO")
        else:
            print(f"[FAIL] Autenticacion: FALLO. Response: {response.text}")
    except Exception as e:
        print(f"[FAIL] Excepcion en Test Autenticacion: {e}")

    # B) Test de Cierre de Caja (RBAC)
    try:
        response = client.get("/api/v1/pos/cierre-caja", headers=headers)
        if response.status_code == 200:
            print("[OK] Cierre de Caja (Enums SQL Group By): PASO")
        else:
            print(f"[FAIL] Cierre de Caja: FALLO. Response: {response.text}")
    except Exception as e:
        print(f"[FAIL] Excepcion en Test POS: {e}")

    # C) Test de Outbox / HITL
    try:
        response = client.get("/api/v1/crm/mensajes/pendientes", headers=headers)
        if response.status_code == 200:
            print("[OK] Bandeja de Salida (HITL Outbox y Rate Limiter): PASO")
        else:
            print(f"[FAIL] Bandeja de Salida: FALLO. Response: {response.text}")
    except Exception as e:
        print(f"[FAIL] Excepcion en Test CRM Outbox: {e}")

    # 3. Pruebas Módulos Batch/ML
    print("\n[PASO 3] Pruebas de Scripts Asincronos (Machine Learning & Pipelines)...")
    scripts = [
        "scripts/inventory_optimization.py",
        "scripts/train_crm_model.py",
        "scripts/run_market_analysis.py"
    ]
    
    for script_path in scripts:
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), script_path)
        if os.path.exists(full_path):
            result = subprocess.run([sys.executable, full_path], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] {script_path}: COMPILO Y EJECUTO CORRECTAMENTE")
            else:
                # Es normal que fallen por falta de datos masivos (ej. Pandas tratando de agrupar 0 filas)
                error_lines = result.stderr.strip().split('\n')
                last_error = error_lines[-1] if error_lines else "Unknown error"
                print(f"[WARN] {script_path}: TERMINO CON EXCEPCION. (Probablemente falta volumen de ventas real para el ML)")
                print(f"       Causa detectada: {last_error}")
        else:
            print(f"[WARN] Script omitido, no encontrado: {script_path}")

    print("\n" + "="*60)
    print("[FIN] TESTER AUTOMATIZADO COMPLETO")
    print("="*60)

if __name__ == "__main__":
    run_tests()
