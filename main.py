#!/usr/bin/env python3
"""Solinilla Inventory API - Versión Final Corregida"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import BytesIO
import traceback

from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from src.db import init_db, get_conn
from src.auth import verify_password, create_access_token, decode_token
from src.inventory import (
    obtener_usuario_por_username, obtener_productos, crear_producto, eliminar_producto,
    registrar_movimiento, obtener_movimientos_dia, obtener_cierre_anterior,
    cerrar_inventario_dia, obtener_cierre_por_fecha
)

app = FastAPI(title="Solinilla Inventory API", version="4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
security = HTTPBearer()

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

def require_auth(auth: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = decode_token(auth.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except Exception as e:
        print(f"Error auth: {e}")
        raise HTTPException(status_code=401, detail="No autorizado")

def check_url_token(token: Optional[str] = Query(None), authorization: Optional[str] = None) -> dict:
    try:
        auth_token = authorization.replace("Bearer ", "").strip() if authorization else (token.strip() if token else None)
        user = decode_token(auth_token) if auth_token else None
        if not user:
            raise HTTPException(status_code=401, detail="No autenticado")
        return user
    except Exception as e:
        print(f"Error token URL: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")

@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        print("✅ Solinilla API iniciada correctamente")
    except Exception as e:
        print(f"❌ Error en startup: {e}")
        traceback.print_exc()

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/api/login")
def login(data: LoginRequest):
    try:
        user = obtener_usuario_por_username(data.username)
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        token = create_access_token({"sub": user["username"], "rol": user["rol"]})
        return {"access_token": token, "token_type": "bearer", "user": {"username": user["username"], "rol": user["rol"]}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error login: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/productos")
def get_prods(user: dict = Depends(require_auth)):
    try:
        productos = obtener_productos()
        return {"productos": productos}
    except Exception as e:
        print(f"Error productos: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/productos")
def add_prod(p: ProductoCreate, user: dict = Depends(require_auth)):
    try:
        ok, msg = crear_producto(p.id, p.nombre, p.stock, p.fecha_vencimiento)
        if ok:
            return {"msg": msg, "success": True}
        raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error crear producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/productos/{pid}")
def del_prod(pid: str, user: dict = Depends(require_auth)):
    try:
        ok, msg = eliminar_producto(pid)
        if ok:
            return {"msg": msg, "success": True}
        raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos")
def get_movs(fecha: Optional[str] = None, user: dict = Depends(require_auth)):
    try:
        fecha = fecha or datetime.now().date().isoformat()
        movimientos = obtener_movimientos_dia(fecha)
        return {"movimientos": movimientos}
    except Exception as e:
        print(f"Error movimientos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/movimientos")
def add_mov(m: MovimientoCreate, user: dict = Depends(require_auth)):
    try:
        print(f"📝 Registrando movimiento: {m.producto_id}, {m.tipo}, {m.cantidad}")
        
        # Validar que el tipo sea correcto
        if m.tipo not in ['entrada', 'salida', 'baja']:
            raise HTTPException(status_code=400, detail="Tipo inválido. Use: entrada, salida o baja")
        
        ok, msg = registrar_movimiento(m.producto_id, m.tipo, m.cantidad, m.motivo)
        if ok:
            print(f"✅ Movimiento registrado: {msg}")
            return {"msg": msg, "success": True}
        else:
            print(f"❌ Error registrando: {msg}")
            raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error EXCEPTION en movimiento: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/cierre/{fecha}")
def obtener_cierre_api(fecha: str, user: dict = Depends(require_auth)):
    try:
        return {"fecha": fecha, "productos": obtener_cierre_por_fecha(fecha)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cierre")
def cerrar_inventario_api(request: Request, fecha: str = Query(...), user: dict = Depends(require_auth)):
    """
    Cierra el inventario del día y ACTUALIZA el stock real.
    Incluye: Entradas, Ventas (salidas) y Bajas (mermas).
    """
    conn = None
    try:
        productos = obtener_productos()
        movimientos = obtener_movimientos_dia(fecha)
        productos_con_cierre = []
        
        for prod in productos:
            # 1. Obtener cierre anterior
            cierre_ant = obtener_cierre_anterior(prod['id'], fecha)
            
            if cierre_ant:
                inv_ini = cierre_ant['inv_final']
            else:
                inv_ini = prod['stock']
            
            # 2. Calcular movimientos del día
            entra = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'entrada')
            ventas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'salida')
            bajas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'baja')
            
            # 3. Calcular INV FINAL (resta ventas Y bajas)
            inv_final = inv_ini + entra - ventas - bajas
            
            productos_con_cierre.append({
                'producto_id': prod['id'],
                'inv_ini': inv_ini,
                'entra': entra,
                'ventas': ventas,
                'bajas': bajas,  # ✅ Ahora sí incluye las bajas
                'inv_final': inv_final,
                'observaciones': ''
            })
        
        # 4. Guardar cierre
        ok, msg = cerrar_inventario_dia(fecha, productos_con_cierre, user.get('sub', 'admin'))
        
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        
        # 5. ACTUALIZAR STOCK REAL
        conn = get_conn()
        cur = conn.cursor()
        
        for prod_cierre in productos_con_cierre:
            cur.execute("""
                UPDATE productos 
                SET stock = %s 
                WHERE id = %s
            """, (prod_cierre['inv_final'], prod_cierre['producto_id']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "msg": f"✅ Inventario cerrado. {len(productos_con_cierre)} productos actualizados.",
            "success": True,
            "fecha": fecha
        }
        
    except HTTPException:
        if conn:
            conn.close()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"❌ Error cerrando inventario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al cerrar: {str(e)}")
# ==========================================
# 📋 MAPEO DE CATEGORÍAS (DEBE IR ANTES DE calcular_inventario)
# ==========================================
CATEGORIA_MAP = {
    "SODA HADSU": "BEBIDAS",
    "COCACOLAPET 250ML": "BEBIDAS",
    "GINGER DRY 300ML": "BEBIDAS",
    "COCA COLA PET 400": "BEBIDAS",
    "POSTOBON PET 400": "BEBIDAS",
    "COCA COLA ZERO 400": "BEBIDAS",
    "GATORADE": "BEBIDAS",
    "CERVEZA AGUILA LIGHT": "BEBIDAS",
    "CERVEZA AGUILA NEGRA": "BEBIDAS",
    "CERVEZA CLUB COLOMBIA": "BEBIDAS",
    "CERVEZA STELLA": "BEBIDAS",
    "AGUA PET 600": "BEBIDAS",
    "TE HATSU 500 ML": "BEBIDAS",
    "CERVEZA CORONA 330ML": "BEBIDAS",
    "SODA SCHWEPPERS": "BEBIDAS",
    "AGUARDIENTE 375": "RON Y VINOS",
    "AGUARDIENTE 750": "RON Y VINOS",
    "BUCHANNA 375": "RON Y VINOS",
    "BUCHANNA 750": "RON Y VINOS",
    "OLD PARR 750": "RON Y VINOS",
    "RON CALDAS 375": "RON Y VINOS",
    "RON MEDELLIN 375": "RON Y VINOS",
    "RON MEDELLIN 750": "RON Y VINOS",
    "TEQUILA JOSE CUERVO 750": "RON Y VINOS",
    "TRIPLESECC": "RON Y VINOS",
    "V.BLANCO S.B SANTA RITA 750": "RON Y VINOS",
    "V.TINTO C.B 750 SANT RITA": "RON Y VINOS",
    "V.TINTO POLERO 750ML": "RON Y VINOS",
    "PULPA DE FRESA 90GR": "PULPAS Y FRUTAS",
    "PULPA DE MANGO 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE MARACUYA 90 GR": "PULPAS Y FRUTAS",
    "PULPA LULO 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE MORA 90 GR": "PULPAS Y FRUTAS",
    "PULPA GUANABANA 90 GR": "PULPAS Y FRUTAS",
    "PULPA DE COROZO KL": "PULPAS Y FRUTAS",
    "LIMON": "PULPAS Y FRUTAS",
    "NARANJA": "PULPAS Y FRUTAS",
    "CHOCO CONO": "HELADOS Y POSTRES",
    "HELADO DE GALLETA": "HELADOS Y POSTRES",
    "PALETA CHOCO BREACK": "HELADOS Y POSTRES",
    "HELADO CASERO": "HELADOS Y POSTRES",
    "POSTRES DE LA CASA": "HELADOS Y POSTRES",
    "CREMA DE COCO": "HELADOS Y POSTRES",
    "CEREZA": "HELADOS Y POSTRES",
    "CREMA DE LECHE": "HELADOS Y POSTRES",
    "V.BLANCO POLERO": "HELADOS Y POSTRES",
    "AZUCAR POR KILO": "HELADOS Y POSTRES",
    "CAFÉ POR SOBRE": "HELADOS Y POSTRES"
}

# ==========================================
# 📊 FUNCIÓN DE CÁLCULO DE INVENTARIO
# ==========================================
def calcular_inventario(productos: List[dict], movimientos: List[dict], fecha: str) -> Dict[str, List[dict]]:
    cats = {"BEBIDAS": [], "RON Y VINOS": [], "PULPAS Y FRUTAS": [], "HELADOS Y POSTRES": []}
    seen_ids = set()
    
    for prod in productos:
        if prod['id'] in seen_ids:
            continue
        seen_ids.add(prod['id'])
        
        cat = CATEGORIA_MAP.get(prod['nombre'], "BEBIDAS")
        cierre_ant = obtener_cierre_anterior(prod['id'], fecha)
        inv_ini = cierre_ant['inv_final'] if cierre_ant else 0
        
        # ✅ Calcular entradas, ventas y BAJAS por separado
        entra = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'entrada')
        ventas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'salida')
        bajas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == prod['id'] and m['tipo'] == 'baja')
        
        total = inv_ini + entra
        # ✅ El final descuenta tanto ventas como bajas
        inv_final = total - ventas - bajas
        
        cats[cat].append({
            'nombre': prod['nombre'],
            'inv_ini': inv_ini if inv_ini != 0 else '',
            'entra': entra if entra != 0 else '',
            'total': total if total != 0 else '',
            'ventas': ventas if ventas != 0 else '',
            'inv_final': inv_final if inv_final != 0 else '',
            'bajas': bajas if bajas != 0 else '',
            'observaciones': ''
        })
    
    for cat in cats:
        cats[cat] = sorted(cats[cat], key=lambda x: x['nombre'])
    return cats
# ==========================================
# 📄 ENDPOINT DE PDF
# ==========================================
@app.get("/api/reporte/pdf")
def generar_pdf(fecha: str = Query(...), user: dict = Depends(check_url_token)):
    try:
        productos = obtener_productos()
        movimientos = obtener_movimientos_dia(fecha)
        cats = calcular_inventario(productos, movimientos, fecha)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                                rightMargin=0.4*inch, leftMargin=0.4*inch, 
                                topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        
        elements.append(Paragraph("INVENTARIO RESTAURANTE", 
                                 ParagraphStyle('Title', fontSize=14, alignment=1, fontName='Helvetica-Bold', spaceAfter=4)))
        elements.append(Paragraph(f"FECHA: {fecha}", 
                                 ParagraphStyle('Date', fontSize=10, alignment=1, spaceAfter=8)))
        
        data = [['PRODUCTOS', 'INV. INI', 'ENTRA', 'TOTAL', 'VENTAS', 'INV. FINAL', 'BAJAS', 'OBSERVACIONES']]
        col_widths = [2.6*inch, 0.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.9*inch, 0.6*inch, 1.5*inch]
        
        orden_categorias = ["BEBIDAS", "RON Y VINOS", "PULPAS Y FRUTAS", "HELADOS Y POSTRES"]
        
        for cat_name in orden_categorias:
            if cat_name in cats and cats[cat_name]:
                data.append([cat_name, '', '', '', '', '', '', ''])
                
                for prod in cats[cat_name]:
                    data.append([
                        prod['nombre'],
                        str(prod['inv_ini']) if prod['inv_ini'] != '' else '',
                        str(prod['entra']) if prod['entra'] != '' else '',
                        str(prod['total']) if prod['total'] != '' else '',
                        str(prod['ventas']) if prod['ventas'] != '' else '',
                        str(prod['inv_final']) if prod['inv_final'] != '' else '',
                        prod['bajas'],
                        prod['observaciones']
                    ])
        
        table = Table(data, colWidths=col_widths)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ])
        
        current_row = 1
        for cat_name in orden_categorias:
            if cat_name in cats and cats[cat_name]:
                len_cat = len(cats[cat_name])
                table_style.add('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor('#d0d0d0'))
                table_style.add('FONTNAME', (0, current_row), (0, current_row), 'Helvetica-Bold')
                table_style.add('SPAN', (0, current_row), (-1, current_row))
                table_style.add('ALIGN', (0, current_row), (-1, current_row), 'CENTER')
                table_style.add('FONTSIZE', (0, current_row), (-1, current_row), 9)
                current_row += 1
                current_row += len_cat
        
        table.setStyle(table_style)
        elements.append(table)
        
        elements.append(Spacer(1, 0.4*inch))
        firmas_data = [
            ['NOMBRE INV INICIAL:', '', 'NOMBRE INV FINAL:', ''],
            ['_________________________', '', '_________________________', '']
        ]
        firmas_table = Table(firmas_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        firmas_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(firmas_table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return StreamingResponse(buffer, media_type="application/pdf", 
                                headers={"Content-Disposition": f"inline; filename=inventario_{fecha}.pdf"})
    except Exception as e:
        print(f"❌ ERROR PDF: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@app.get("/api/health")
def health():
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ ERROR GLOBAL: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno: {str(exc)}"}
    )