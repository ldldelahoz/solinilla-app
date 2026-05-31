#!/usr/bin/env python3
<<<<<<< HEAD
"""Solinilla Inventory API - Con cierre de inventario diario"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from src.db import init_db
from src.auth import verify_password, create_access_token, decode_token
from src.inventory import (
    obtener_usuario_por_username, obtener_productos, crear_producto, eliminar_producto,
    registrar_movimiento, obtener_movimientos_dia, obtener_cierre_anterior,
    cerrar_inventario_dia, obtener_cierre_por_fecha
)

# === INICIALIZACIÓN ===
app = FastAPI(title="Solinilla Inventory API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
security = HTTPBearer()

# === MODELOS PYDANTIC ===
=======
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
>>>>>>> 689b273a268eab275c927706c27abae2ce1d9aec
class LoginRequest(BaseModel):
    username: str
    password: str

class ProductoCreate(BaseModel):
    id: str
    nombre: str
<<<<<<< HEAD
    stock: float = 0.0
    fecha_vencimiento: Optional[str] = None

class MovimientoCreate(BaseModel):
    producto_id: str
    tipo: str
    cantidad: float
    motivo: Optional[str] = None

# === DEPENDENCIAS ===
def require_auth(auth: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="No autorizado", headers={"WWW-Authenticate": "Bearer"})
    return payload

def check_url_token(token: Optional[str] = Query(None), authorization: Optional[str] = None) -> dict:
    auth_token = authorization.replace("Bearer ", "").strip() if authorization else (token.strip() if token else None)
    user = decode_token(auth_token) if auth_token else None
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user

# === STARTUP ===
@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Solinilla API iniciada")

# === RUTAS PÚBLICAS ===
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# === AUTH ===
@app.post("/api/login")
def login(data: LoginRequest):
    user = obtener_usuario_por_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token({"sub": user["username"], "rol": user["rol"]})
    return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "rol": user["rol"]}}

# === PRODUCTOS ===
@app.get("/api/productos")
def get_prods(user: dict = Depends(require_auth)):
    return {"productos": obtener_productos()}

@app.post("/api/productos")
def add_prod(p: ProductoCreate, user: dict = Depends(require_auth)):
    ok, msg = crear_producto(p.id, p.nombre, p.stock, p.fecha_vencimiento)
    return {"msg": msg} if ok else HTTPException(400, msg)

@app.delete("/api/productos/{pid}")
def del_prod(pid: str, user: dict = Depends(require_auth)):
    ok, msg = eliminar_producto(pid)
    return {"msg": msg} if ok else HTTPException(400, msg)

# === MOVIMIENTOS ===
@app.get("/api/movimientos")
def get_movs(fecha: Optional[str] = None, user: dict = Depends(require_auth)):
    fecha = fecha or datetime.now().date().isoformat()
    return {"movimientos": obtener_movimientos_dia(fecha)}

@app.post("/api/movimientos")
def add_mov(m: MovimientoCreate, user: dict = Depends(require_auth)):
    ok, msg = registrar_movimiento(m.producto_id, m.tipo, m.cantidad, m.motivo)
    return {"msg": msg} if ok else HTTPException(400, msg)

# === CIERRE DE INVENTARIO ===
@app.get("/api/cierre/{fecha}")
def obtener_cierre_api(fecha: str, user: dict = Depends(require_auth)):
    return {"fecha": fecha, "productos": obtener_cierre_por_fecha(fecha)}

@app.post("/api/cierre")
def cerrar_inventario_api(request: Request, fecha: str = Query(...), user: dict = Depends(require_auth)):
    productos = obtener_productos()
    movimientos = obtener_movimientos_dia(fecha)
    productos_con_cierre = []
    
    for prod in productos:
        cierre_ant = obtener_cierre_anterior(prod['id'], fecha)
        inv_ini = cierre_ant['inv_final'] if cierre_ant else 0
        entra = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'entrada')
        ventas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'salida')
        inv_final = inv_ini + entra - ventas
        
        productos_con_cierre.append({
            'producto_id': prod['id'],
            'inv_ini': inv_ini,
            'entra': entra,
            'ventas': ventas,
            'bajas': 0,
            'inv_final': inv_final,
            'observaciones': ''
        })
    
    ok, msg = cerrar_inventario_dia(fecha, productos_con_cierre, user.get('sub', 'admin'))
    return {"msg": msg} if ok else HTTPException(400, msg)

# === MAPEO DE CATEGORÍAS ===
CATEGORIA_MAP = {
    "SODA HADSU": "BEBIDAS", "COCACOLAPET 250ML": "BEBIDAS", "GINGER DRY 300ML": "BEBIDAS",
    "COCA COLA PET 400": "BEBIDAS", "POSTOBON PET 400": "BEBIDAS", "COCA COLA ZERO 400": "BEBIDAS",
    "GATORADE": "BEBIDAS", "CERVEZA AGUILA LIGHT": "BEBIDAS", "CERVEZA AGUILA NEGRA": "BEBIDAS",
    "CERVEZA CLUB COLOMBIA": "BEBIDAS", "CERVEZA STELLA": "BEBIDAS", "AGUA PET 600": "BEBIDAS",
    "TE HATSU 500 ML": "BEBIDAS", "CERVEZA CORONA 330ML": "BEBIDAS", "SODA SCHWEPPERS": "BEBIDAS",
    "AGUARDIENTE 375": "RON Y VINOS", "AGUARDIENTE 750": "RON Y VINOS", "BUCHANNA 375": "RON Y VINOS",
    "BUCHANNA 750": "RON Y VINOS", "OLD PARR 750": "RON Y VINOS", "RON CALDAS 375": "RON Y VINOS",
    "RON MEDELLIN 375": "RON Y VINOS", "RON MEDELLIN 750": "RON Y VINOS", "TEQUILA JOSE CUERVO 750": "RON Y VINOS",
    "TRIPLESECC": "RON Y VINOS", "V.BLANCO S.B SANTA RITA 750": "RON Y VINOS",
    "V.TINTO C.B 750 SANT RITA": "RON Y VINOS", "V.TINTO POLERO 750ML": "RON Y VINOS",
    "PULPA DE FRESA 90GR": "PULPAS Y FRUTAS", "PULPA DE MANGO 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE MARACUYA 90 GR": "PULPAS Y FRUTAS", "PULPA LULO 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE MORA 90 GR": "PULPAS Y FRUTAS", "PULPA GUANABANA 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE COROZO KL": "PULPAS Y FRUTAS", "LIMON": "PULPAS Y FRUTAS", "NARANJA": "PULPAS Y FRUTAS",
    "CHOCO CONO": "HELADOS Y POSTRES", "HELADO DE GALLETA": "HELADOS Y POSTRES",
    "PALETA CHOCO BREACK": "HELADOS Y POSTRES", "HELADO CASERO": "HELADOS Y POSTRES",
    "POSTRES DE LA CASA": "HELADOS Y POSTRES", "CREMA DE COCO": "HELADOS Y POSTRES",
    "CEREZA": "HELADOS Y POSTRES", "CREMA DE LECHE": "HELADOS Y POSTRES",
    "V.BLANCO POLERO": "HELADOS Y POSTRES", "AZUCAR POR KILO": "HELADOS Y POSTRES", "CAFÉ POR SOBRE": "HELADOS Y POSTRES"
}

# === CÁLCULO DE INVENTARIO ===
def calcular_inventario(productos: List[dict], movimientos: List[dict], fecha: str) -> Dict[str, List[dict]]:
    cats = {"BEBIDAS": [], "RON Y VINOS": [], "PULPAS Y FRUTAS": [], "HELADOS Y POSTRES": []}
    for prod in productos:
        cat = CATEGORIA_MAP.get(prod['nombre'], "BEBIDAS")
        cierre_ant = obtener_cierre_anterior(prod['id'], fecha)
        inv_ini = cierre_ant['inv_final'] if cierre_ant else 0
        entra = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'entrada')
        ventas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'salida')
        cats[cat].append({
            'id': prod['id'],
            'nombre': prod['nombre'],
            'inv_ini': inv_ini,
            'entra': entra,
            'total': inv_ini + entra,
            'ventas': ventas,
            'inv_final': inv_ini + entra - ventas,
            'bajas': 0,
            'observaciones': ''
        })
    for cat in cats:
        cats[cat] = sorted(cats[cat], key=lambda x: x['nombre'])
    return cats

# === REPORTES ===
@app.get("/api/reporte/imprimir", response_class=HTMLResponse)
def print_view(request: Request, fecha: Optional[str] = Query(None), user: dict = Depends(check_url_token)):
    fecha = fecha or datetime.now().date().isoformat()
    productos = obtener_productos()
    movimientos = obtener_movimientos_dia(fecha)
    cats = calcular_inventario(productos, movimientos, fecha)
    return templates.TemplateResponse("print_view.html", {
        "request": request,
        "fecha": fecha,
        "categorias": [{"nombre": c, "productos": p} for c, p in cats.items() if p]
    })

@app.get("/api/reporte/pdf")
def generar_pdf(fecha: str = Query(...), user: dict = Depends(check_url_token)):
    productos = obtener_productos()
    movimientos = obtener_movimientos_dia(fecha)
    cats = calcular_inventario(productos, movimientos, fecha)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements, styles = [], getSampleStyleSheet()
    
    elements.append(Paragraph("INVENTARIO RESTAURANTE", ParagraphStyle('T', parent=styles['Heading1'], fontSize=14, alignment=1, spaceAfter=5)))
    elements.append(Paragraph(f"FECHA: {fecha}", ParagraphStyle('S', alignment=1, spaceAfter=12, fontSize=10)))
    
    data = [['PRODUCTOS', 'INV.INI', 'ENTRA', 'TOTAL', 'VENTAS', 'INV.FINAL', 'BAJAS', 'OBSERV.']]
    for cat in ["BEBIDAS", "RON Y VINOS", "PULPAS Y FRUTAS", "HELADOS Y POSTRES"]:
        for prod in cats.get(cat, []):
            data.append([
                prod['nombre'],
                str(prod['inv_ini']),
                str(prod['entra']),
                str(prod['total']),
                str(prod['ventas']),
                str(prod['inv_final']),
                '', ''
            ])
    
    table = Table(data, colWidths=[2.3*inch, 0.65*inch, 0.65*inch, 0.65*inch, 0.65*inch, 0.85*inch, 0.55*inch, 0.9*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.beige]),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=inventario_{fecha}.pdf"})

# === HEALTH ===
@app.get("/api/health")
def health():
    return {"status": "alive", "app": "solinilla-api", "version": "2.0", "timestamp": datetime.utcnow().isoformat()}
=======
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



# === ENDPOINT DE DEBUG PARA AUTH (eliminar después de probar) ===
@app.get("/api/debug/auth-test")
async def debug_auth_test():
    """Prueba directa de verificación de contraseña."""
    from src.auth import pwd_context, verify_password
    
    test_password = "Admin2026!"
    
    # Obtener hash real de la BD
    from src.inventory import obtener_usuario_por_username
    user = obtener_usuario_por_username("admin")
    
    if not user:
        return {"error": "Usuario admin no encontrado en BD"}
    
    stored_hash = user.get("password_hash", "")
    
    # Verificar manualmente
    is_valid = verify_password(test_password, stored_hash)
    
    return {
        "password_tested": test_password,
        "stored_hash_prefix": stored_hash.split("$")[1] if "$" in stored_hash else "unknown",
        "pwd_context_schemes": list(pwd_context.schemes()),
        "verification_result": is_valid,
        "hash_match": stored_hash.startswith("$pbkdf2-sha256$")
    }


@app.get("/api/deep-debug")
async def deep_debug_auth():
    try:
        from src.db import get_conn
        from src.auth import verify_password, pwd_context
        
        response = {
            "db_status": "checking...",
            "user_found": False,
            "hash_prefix": "N/A",
            "password_check": "N/A",
            "pwd_schemes": list(pwd_context.schemes())
        }

        # 1. Intentar conectar a la BD que usa Render
        with get_conn() as conn:
            response["db_status"] = "connected"
            with conn.cursor() as cur:
                # 2. Buscar usuario admin
                cur.execute("SELECT username, password_hash FROM usuarios WHERE username = %s", ("admin",))
                user = cur.fetchone()
                
                if user:
                    response["user_found"] = True
                    # Obtener el hash (compatible con dict y tuple)
                    hash_val = user['password_hash'] if hasattr(user, 'keys') else user[1]
                    response["hash_prefix"] = hash_val.split('$')[1] if '$' in hash_val else "unknown"
                    
                    # 3. Verificar la contraseña "Admin2026!" con el hash de la BD
                    is_valid = verify_password("Admin2026!", hash_val)
                    response["password_check"] = "✅ CORRECTO" if is_valid else "❌ INCORRECTO"
                else:
                    response["error"] = "El usuario 'admin' NO EXISTE en esta base de datos."
                    
        return response

    except Exception as e:
        return {"error": str(e), "trace": str(e)}
>>>>>>> 689b273a268eab275c927706c27abae2ce1d9aec
