import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import timedelta
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import Depends, HTTPException, status
from src.auth import get_current_user 

from src.db import init_db, get_conn
from src.auth import (
    create_access_token, verify_password, hash_password,
    get_current_user, require_admin, ACCESS_TOKEN_EXPIRE_MINUTES
)
from src import inventory
# === ENDPOINT DE SALUD MÍNIMO ===
@app.get("/api/health")
async def health_check():
    return {"status": "alive", "app": "solinilla-cloud"}
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="🍽️ Sistema de Inventarios Restaurante Solinilla", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# 📦 Modelos Pydantic
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    rol: str = "usuario"

class ProductoCreate(BaseModel):
    id: str
    nombre: str
    fecha_vencimiento: Optional[str] = ""

class MovimientoCreate(BaseModel):
    id_prod: str
    tipo: str  # "entrada" o "salida"
    cantidad: float
    motivo: str

# 🌐 Rutas Web
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={})

# 🔐 API: Login
@app.post("/api/login")
async def login(data: LoginRequest):
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM usuarios WHERE username=?", (data.username,)).fetchone()
    
    if not user and data.username.lower() == "admin" and data.password == "Solinilla2026!":
        hashed = hash_password("Solinilla2026!")
        with get_conn() as conn:
            conn.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?, ?, ?)",
                         ("admin", hashed, "admin"))
        user = {"username": "admin", "password_hash": hashed, "rol": "admin"}

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = create_access_token(
        data={"sub": user["username"], "rol": user["rol"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer", "rol": user["rol"]}

# 🛡️ API: Crear usuario (Solo Admin)
@app.post("/api/admin/crear-usuario")
async def crear_usuario(data: UserCreate, admin: dict = Depends(require_admin)):
    with get_conn() as conn:
        try:
            hashed = hash_password(data.password)
            conn.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?, ?, ?)",
                         (data.username, hashed, data.rol))
            return {"msg": f"✅ Usuario {data.username} creado."}
        except Exception:
            raise HTTPException(status_code=400, detail="El usuario ya existe.")

# 📦 API: Gestión de Inventario


@app.get("/api/productos")
async def obtener_productos(current_user: dict = Depends(get_current_user)):
    """Obtiene todos los productos (requiere autenticación vía header)."""
    try:
        from src.inventory import obtener_productos as get_products_db
        productos = get_products_db()
        return {"productos": productos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener productos: {str(e)}")

@app.post("/api/productos")
async def crear_prod(data: ProductoCreate, user: dict = Depends(require_admin)):
    ok, msg = inventory.crear_producto(data.id, data.nombre, data.fecha_vencimiento)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}

@app.post("/api/movimientos")
async def registrar_mov(data: MovimientoCreate, user: dict = Depends(get_current_user)):
    ok, msg = inventory.registrar_movimiento(data.id_prod, data.tipo, data.cantidad, data.motivo)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}

@app.get("/api/reporte")
async def get_reporte(fecha: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    return inventory.generar_reporte(fecha)

# ... (mantén todo el código anterior de main.py hasta antes del if __name__)

# Agrega estas NUEVAS rutas antes del if __name__ == "__main__":

@app.get("/api/productos/buscar")
async def buscar_prods(q: str = Query(..., min_length=1), user: dict = Depends(get_current_user)):
    """Busca productos por ID o nombre para el selector"""
    return {"productos": inventory.buscar_productos(q)}

@app.get("/api/movimientos/dia")
async def get_movimientos_dia(fecha: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Obtiene todos los movimientos del día"""
    return {"movimientos": inventory.obtener_movimientos_dia(fecha)}

@app.put("/api/movimientos/{mov_id}")
async def put_movimiento(mov_id: int, data: MovimientoCreate, user: dict = Depends(require_admin)):
    """Edita un movimiento existente"""
    ok, msg = inventory.editar_movimiento(mov_id, data.cantidad, data.motivo)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}

@app.delete("/api/movimientos/{mov_id}")
async def delete_movimiento(mov_id: int, user: dict = Depends(require_admin)):
    """Elimina un movimiento"""
    ok, msg = inventory.eliminar_movimiento(mov_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}

@app.post("/api/inventario/cerrar")
async def cerrar_inv(
    data: dict,  # {"fecha": "2026-05-28", "observaciones": "..."}
    user: dict = Depends(require_admin)
):
    """Cierra el inventario del día"""
    fecha = data.get("fecha")
    obs = data.get("observaciones", "")
    ok, msg = inventory.cerrar_inventario_dia(fecha, obs)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}
@app.get("/api/hoja-inventario")
async def get_hoja_impresion(fecha: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Devuelve datos formateados para la hoja de inventario diario"""
    return inventory.generar_hoja_impresion(fecha)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)