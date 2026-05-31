#!/usr/bin/env python3
"""Solinilla Inventory API - Versión Final Corregida"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

from src.db import init_db
from src.auth import verify_password, create_access_token, decode_token
from src.inventory import (
    obtener_usuario_por_username, obtener_productos, crear_producto, eliminar_producto,
    registrar_movimiento, obtener_movimientos_dia, obtener_cierre_anterior,
    cerrar_inventario_dia, obtener_cierre_por_fecha
)

app = FastAPI(title="Solinilla Inventory API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
security = HTTPBearer()

# --- Modelos ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ProductoCreate(BaseModel):
    id: str
    nombre: str
    stock: float = 0.0
    fecha_vencimiento: Optional[str] = None

class MovimientoCreate(BaseModel):
    producto_id: str
    tipo: str
    cantidad: float
    motivo: Optional[str] = None

# --- Auth ---
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

@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Solinilla API iniciada")

# --- Rutas HTML ---
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# --- Login ---
@app.post("/api/login")
def login(data: LoginRequest):
    user = obtener_usuario_por_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token({"sub": user["username"], "rol": user["rol"]})
    return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "rol": user["rol"]}}

# --- Productos ---
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

# --- Movimientos ---
@app.get("/api/movimientos")
def get_movs(fecha: Optional[str] = None, user: dict = Depends(require_auth)):
    fecha = fecha or datetime.now().date().isoformat()
    return {"movimientos": obtener_movimientos_dia(fecha)}

@app.post("/api/movimientos")
def add_mov(m: MovimientoCreate, user: dict = Depends(require_auth)):
    ok, msg = registrar_movimiento(m.producto_id, m.tipo, m.cantidad, m.motivo)
    return {"msg": msg} if ok else HTTPException(400, msg)

# --- Cierre ---
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
            'producto_id': prod['id'], 'inv_ini': inv_ini, 'entra': entra,
            'ventas': ventas, 'bajas': 0, 'inv_final': inv_final, 'observaciones': ''
        })
    ok, msg = cerrar_inventario_dia(fecha, productos_con_cierre, user.get('sub', 'admin'))
    return {"msg": msg} if ok else HTTPException(400, msg)

# --- Lógica de Reportes y PDF ---

# Mapeo de categorías EXACTO para el reporte
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

def calcular_inventario(productos: List[dict], movimientos: List[dict], fecha: str) -> Dict[str, List[dict]]:
    cats = {"BEBIDAS": [], "RON Y VINOS": [], "PULPAS Y FRUTAS": [], "HELADOS Y POSTRES": []}
    for prod in productos:
        cat = CATEGORIA_MAP.get(prod['nombre'], "BEBIDAS") # Default a Bebidas si no encuentra
        cierre_ant = obtener_cierre_anterior(prod['id'], fecha)
        inv_ini = cierre_ant['inv_final'] if cierre_ant else 0
        entra = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'entrada')
        ventas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'salida')
        
        # Formato limpio para el PDF
        item = {
            'nombre': prod['nombre'], 
            'inv_ini': inv_ini if inv_ini != 0 else '', 
            'entra': entra if entra != 0 else '',
            'total': (inv_ini + entra) if (inv_ini + entra) != 0 else '',
            'ventas': ventas if ventas != 0 else '',
            'inv_final': (inv_ini + entra - ventas) if (inv_ini + entra - ventas) != 0 else '',
            'bajas': '',
            'observaciones': ''
        }
        cats[cat].append(item)
    
    for cat in cats:
        cats[cat] = sorted(cats[cat], key=lambda x: x['nombre'])
    return cats

@app.get("/api/reporte/pdf")
def generar_pdf(fecha: str = Query(...), user: dict = Depends(check_url_token)):
    productos = obtener_productos()
    movimientos = obtener_movimientos_dia(fecha)
    cats = calcular_inventario(productos, movimientos, fecha)
    
    buffer = BytesIO()
    # Formato Horizontal (Landscape) para que quepa la tabla ancha
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    
    # Título
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterTitle', alignment=1, fontSize=14, fontName='Helvetica-Bold', spaceAfter=10))
    elements.append(Paragraph(f"INVENTARIO RESTAURANTE SOLINILLA - {fecha}", styles['CenterTitle']))
    
    # Datos de la tabla
    data = [['PRODUCTOS', 'INV.INI', 'ENTRA', 'TOTAL', 'VENTAS', 'INV.FINAL', 'BAJAS', 'OBSERVACIONES']]
    
    # Definir anchos de columna proporcionales al ancho de la página
    col_widths = [2.5*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 1*inch, 0.8*inch, 2*inch]
    
    for cat_name in ["BEBIDAS", "RON Y VINOS", "PULPAS Y FRUTAS", "HELADOS Y POSTRES"]:
        if cat_name in cats and cats[cat_name]:
            # Fila de Categoría (Fondo Gris)
            data.append([cat_name, '', '', '', '', '', '', ''])
            
            for prod in cats[cat_name]:
                data.append([
                    prod['nombre'],
                    str(prod['inv_ini']),
                    str(prod['entra']),
                    str(prod['total']),
                    str(prod['ventas']),
                    str(prod['inv_final']),
                    prod['bajas'],
                    prod['observaciones']
                ])
    
    # Crear tabla
    table = Table(data, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Alinear nombres a la izquierda
    ])
    
    # Colorear filas de categorías
    current_row = 1
    for cat_name in ["BEBIDAS", "RON Y VINOS", "PULPAS Y FRUTAS", "HELADOS Y POSTRES"]:
        if cat_name in cats and cats[cat_name]:
            len_cat = len(cats[cat_name])
            # Fila de título de categoría
            style.add('BACKGROUND', (0, current_row), (-1, current_row), colors.lightgrey)
            style.add('FONTNAME', (0, current_row), (0, current_row), 'Helvetica-Bold')
            style.add('SPAN', (0, current_row), (-1, current_row)) # Fusionar celdas para el título
            style.add('ALIGN', (0, current_row), (-1, current_row), 'LEFT')
            current_row += 1
            current_row += len_cat # Saltar productos
            
    table.setStyle(style)
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=inventario_{fecha}.pdf"})

@app.get("/api/health")
def health():
    return {"status": "alive"}