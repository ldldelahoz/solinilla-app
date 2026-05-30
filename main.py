#!/usr/bin/env python3
"""Solinilla Inventory API - Main Entry Point"""

from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import sys

# === INSTANCIA DE FASTAPI (PRIMERO, antes de cualquier @app) ===
app = FastAPI(
    title="Solinilla Inventory API",
    description="Sistema de inventario para restaurante",
    version="1.0.0"
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Templates y Static ===
templates = Jinja2Templates(directory="templates")

# === Security ===
security = HTTPBearer()

# === Modelos Pydantic ===
class LoginRequest(BaseModel):
    username: str
    password: str

class ProductoCreate(BaseModel):
    id: str
    nombre: str
    stock: Optional[float] = 0
    fecha_vencimiento: Optional[str] = None

class MovimientoCreate(BaseModel):
    id_prod: str
    tipo: str  # "entrada" o "salida"
    cantidad: float
    motivo: Optional[str] = None

# === ENDPOINTS PÚBLICOS ===

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Página de login."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal (requiere auth en frontend)."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Endpoint de salud para debug."""
    return {
        "status": "alive",
        "app": "solinilla-final",
        "timestamp": datetime.utcnow().isoformat(),
        "python": sys.version
    }

# === AUTH ENDPOINTS ===

@app.post("/api/login")
async def login(data: LoginRequest):
    """Login de usuario y generación de token JWT."""
    from src.auth import verify_password, create_access_token
    from src.inventory import obtener_usuario_por_username
    
    user = obtener_usuario_por_username(data.username)
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(data={"sub": user["username"], "rol": user["rol"]})
    return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "rol": user["rol"]}}

# === DEPENDENCIAS DE AUTH ===

async def get_current_user(authorization: Optional[str] = None):
    """Extrae usuario desde header Authorization: Bearer <token>."""
    from src.auth import decode_token
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    return payload if payload else None

def require_admin(current_user: dict = Depends(get_current_user)):
    """Verifica que el usuario sea admin."""
    if not current_user or current_user.get("rol") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere permisos de administrador"
        )
    return current_user

# === PRODUCTOS ENDPOINTS ===

@app.get("/api/productos")
async def obtener_productos(current_user: dict = Depends(get_current_user)):
    """Obtiene todos los productos (requiere auth)."""
    from src.inventory import obtener_productos
    productos = obtener_productos()
    return {"productos": productos}

@app.post("/api/productos")
async def crear_producto(
    producto: ProductoCreate,
    current_user: dict = Depends(require_admin)
):
    """Crea un nuevo producto (solo admin)."""
    from src.inventory import crear_producto as create_prod_db
    success, msg = create_prod_db(
        producto.id,
        producto.nombre,
        producto.stock or 0,
        producto.fecha_vencimiento
    )
    if success:
        return {"msg": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.delete("/api/productos/{producto_id}")
async def eliminar_producto(
    producto_id: str,
    current_user: dict = Depends(require_admin)
):
    """Elimina un producto por ID (solo admin)."""
    from src.inventory import eliminar_producto as delete_prod_db
    success, msg = delete_prod_db(producto_id)
    if success:
        return {"msg": msg}
    raise HTTPException(status_code=400, detail=msg)

# === MOVIMIENTOS ENDPOINTS ===

@app.get("/api/movimientos")
async def obtener_movimientos(
    fecha: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Obtiene movimientos, filtrando por fecha si se provee."""
    from src.inventory import obtener_movimientos_dia
    if not fecha:
        fecha = datetime.now().date().isoformat()
    movimientos = obtener_movimientos_dia(fecha)
    return {"movimientos": movimientos}

@app.post("/api/movimientos")
async def registrar_movimiento(
    movimiento: MovimientoCreate,
    current_user: dict = Depends(get_current_user)
):
    """Registra entrada o salida de producto."""
    from src.inventory import registrar_movimiento as register_mov_db
    success, msg = register_mov_db(
        movimiento.id_prod,
        movimiento.tipo,
        movimiento.cantidad,
        movimiento.motivo
    )
    if success:
        return {"msg": msg}
    raise HTTPException(status_code=400, detail=msg)

# === CIERRE DE INVENTARIO ===

@app.post("/api/inventario/cerrar")
async def cerrar_inventario(
    fecha: str = Form(...),
    observaciones: str = Form(""),
    current_user: dict = Depends(require_admin)
):
    """Cierra el inventario del día."""
    from src.inventory import cerrar_inventario_dia
    success, msg = cerrar_inventario_dia(fecha, observaciones)
    if success:
        return {"msg": msg}
    raise HTTPException(status_code=400, detail=msg)

# === INICIALIZACIÓN ===

@app.on_event("startup")
async def startup_event():
    """Inicializa la BD al arrancar."""
    from src.db import init_db
    init_db()