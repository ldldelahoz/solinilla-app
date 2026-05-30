import sqlite3
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from datetime import datetime, timedelta
from src.db import get_conn
import logging

logger = logging.getLogger(__name__)

def crear_producto(id_prod: str, nombre: str, fecha_venc: str = "") -> Tuple[bool, str]:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO productos (id, nombre, stock, fecha_vencimiento) VALUES (?, ?, 0, ?)",
                (id_prod.upper(), nombre.strip(), fecha_venc or None)
            )
        logger.info(f"➕ Producto creado: {id_prod}")
        return True, "✅ Producto creado correctamente."
    except sqlite3.IntegrityError:
        return False, "❌ El ID ya existe en el sistema."
    except Exception as e:
        logger.error(f"Error creando producto: {e}")
        return False, f"❌ Error interno: {str(e)}"

def obtener_productos() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, nombre, stock, fecha_vencimiento FROM productos ORDER BY nombre").fetchall()
        return [dict(r) for r in rows]

def buscar_productos(query: str) -> List[Dict]:
    """Busca productos por ID o nombre (para el selector)"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, stock 
            FROM productos 
            WHERE id LIKE ? OR nombre LIKE ?
            ORDER BY nombre
            LIMIT 20
        """, (f"%{query.upper()}%", f"%{query}%")).fetchall()
        return [dict(r) for r in rows]

def registrar_movimiento(id_prod: str, tipo: str, cantidad: float, motivo: str) -> Tuple[bool, str]:
    id_prod = id_prod.upper()
    if cantidad <= 0:
        return False, "❌ La cantidad debe ser mayor a 0."
    
    with get_conn() as conn:
        prod = conn.execute("SELECT stock FROM productos WHERE id=?", (id_prod,)).fetchone()
        if not prod:
            return False, "❌ Producto no encontrado."
        
        stock_actual = prod["stock"]
        if tipo == "salida" and stock_actual < cantidad:
            return False, f"❌ Stock insuficiente. Disponible: {stock_actual}"
        
        nuevo_stock = stock_actual + cantidad if tipo == "entrada" else stock_actual - cantidad
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, id_prod))
        conn.execute(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (?, ?, ?, ?)",
            (id_prod, tipo, cantidad, motivo.strip())
        )
        logger.info(f"📦 {tipo.capitalize()} registrada para {id_prod}: {cantidad} uds.")
        return True, f"✅ {tipo.capitalize()} registrada. Nuevo stock: {nuevo_stock}"

def obtener_movimientos_dia(fecha: str = None) -> List[Dict]:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT m.id, m.fecha, p.nombre, p.id as producto_id, m.tipo, m.cantidad, m.motivo
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.fecha LIKE ?
            ORDER BY m.fecha DESC
        """, (f"{fecha}%",)).fetchall()
        return [dict(r) for r in rows]

def editar_movimiento(mov_id: int, nueva_cantidad: float, nuevo_motivo: str = None) -> Tuple[bool, str]:
    """Edita un movimiento existente y recalcula el stock"""
    if nueva_cantidad <= 0:
        return False, "❌ La cantidad debe ser mayor a 0."
    
    with get_conn() as conn:
        # Obtener movimiento original
        mov = conn.execute("SELECT * FROM movimientos WHERE id=?", (mov_id,)).fetchone()
        if not mov:
            return False, "❌ Movimiento no encontrado."
        
        prod_id = mov["producto_id"]
        tipo = mov["tipo"]
        cantidad_old = mov["cantidad"]
        
        # Calcular diferencia
        diff = nueva_cantidad - cantidad_old
        
        # Actualizar stock del producto
        prod = conn.execute("SELECT stock FROM productos WHERE id=?", (prod_id,)).fetchone()
        nuevo_stock = prod["stock"] + diff if tipo == "entrada" else prod["stock"] - diff
        
        if nuevo_stock < 0:
            return False, f"❌ Stock insuficiente después del cambio. Stock actual: {prod['stock']}"
        
        # Actualizar movimiento y stock
        if nuevo_motivo:
            conn.execute("""
                UPDATE movimientos 
                SET cantidad=?, motivo=? 
                WHERE id=?
            """, (nueva_cantidad, nuevo_motivo.strip(), mov_id))
        else:
            conn.execute("UPDATE movimientos SET cantidad=? WHERE id=?", (nueva_cantidad, mov_id))
        
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, prod_id))
        
        logger.info(f"✏️ Movimiento {mov_id} editado: {cantidad_old} → {nueva_cantidad}")
        return True, f"✅ Movimiento editado. Nuevo stock: {nuevo_stock}"

def eliminar_movimiento(mov_id: int) -> Tuple[bool, str]:
    """Elimina un movimiento y revierte su efecto en el stock"""
    with get_conn() as conn:
        mov = conn.execute("SELECT * FROM movimientos WHERE id=?", (mov_id,)).fetchone()
        if not mov:
            return False, "❌ Movimiento no encontrado."
        
        prod_id = mov["producto_id"]
        tipo = mov["tipo"]
        cantidad = mov["cantidad"]
        
        # Revertir stock
        prod = conn.execute("SELECT stock FROM productos WHERE id=?", (prod_id,)).fetchone()
        nuevo_stock = prod["stock"] - cantidad if tipo == "entrada" else prod["stock"] + cantidad
        
        conn.execute("DELETE FROM movimientos WHERE id=?", (mov_id,))
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, prod_id))
        
        logger.info(f"🗑️ Movimiento {mov_id} eliminado")
        return True, "✅ Movimiento eliminado correctamente."

def generar_reporte(fecha: str = None) -> Dict:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        movs = conn.execute("""
            SELECT m.fecha, p.nombre, m.tipo, m.cantidad, m.motivo 
            FROM movimientos m 
            JOIN productos p ON m.producto_id = p.id 
            WHERE m.fecha LIKE ? 
            ORDER BY m.fecha DESC
        """, (f"{fecha}%",)).fetchall()
        
        stock_actual = conn.execute("SELECT nombre, stock, fecha_vencimiento FROM productos ORDER BY nombre").fetchall()
        
    return {
        "fecha": fecha,
        "movimientos": [dict(m) for m in movs],
        "stock_cierre": [dict(s) for s in stock_actual]
    }



def generar_hoja_impresion(fecha: str = None) -> dict:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
    prev_fecha = (fecha_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    
    with get_conn() as conn:
        #  Snapshot del día solicitado (congela INV. FINAL al momento del cierre)
        snapshot_actual = {row["producto_id"]: row["stock_cierre"] for row in 
                           conn.execute("SELECT producto_id, stock_cierre FROM snapshots_inventario WHERE fecha=?", (fecha,)).fetchall()}
                           
        # 📅 Snapshot del día anterior (base para INV. INI)
        prev_snapshot = {row["producto_id"]: row["stock_cierre"] for row in 
                         conn.execute("SELECT producto_id, stock_cierre FROM snapshots_inventario WHERE fecha=?", (prev_fecha,)).fetchall()}
        
        # 🔄 Movimientos reales del día
        movements = conn.execute("""
            SELECT producto_id, tipo, SUM(cantidad) as cant 
            FROM movimientos WHERE fecha LIKE ? GROUP BY producto_id, tipo
        """, (f"{fecha}%",)).fetchall()
        
        mov_map = {}
        for m in movements:
            mov_map[f"{m['producto_id']}_{m['tipo']}"] = float(m['cant'])
            
        products = conn.execute("SELECT id, nombre, stock FROM productos ORDER BY nombre").fetchall()
        categorias = {"BEBIDAS": [], "RON Y VINOS": [], "PULPAS Y FRUTAS": [], "HELADOS Y POSTRES": [], "VARIOS": []}
        
        for p in products:
            pid, nombre, stock_live = p["id"], p["nombre"], float(p["stock"])
            
            # 🧊 INV. FINAL congelado (o fallback a stock actual si aún no se cerró)
            inv_final = snapshot_actual.get(pid, stock_live)
            
            # 📅 INV. INI del día anterior (o cálculo inverso si es primer día)
            inv_ini = prev_snapshot.get(pid)
            if inv_ini is None:
                entra = mov_map.get(f"{pid}_entrada", 0.0)
                sale = mov_map.get(f"{pid}_salida", 0.0)
                inv_ini = inv_final + sale - entra
            
            entra = mov_map.get(f"{pid}_entrada", 0.0)
            sale = mov_map.get(f"{pid}_salida", 0.0)
            
            cat = "VARIOS"
            if pid.startswith("BEB"): cat = "BEBIDAS"
            elif pid.startswith("LIC"): cat = "RON Y VINOS"
            elif pid.startswith("FRU"): cat = "PULPAS Y FRUTAS"
            elif pid.startswith("HEL"): cat = "HELADOS Y POSTRES"
            
            categorias[cat].append({
                "nombre": nombre,
                "inv_ini": inv_ini,
                "entra": entra,
                "total": inv_ini + entra,
                "ventas_bajas": sale,
                "inv_final": inv_final  #  Congelado al cierre
            })
            
    return {"fecha": fecha, "categorias": {k: v for k, v in categorias.items() if v}}

def cerrar_inventario_dia(fecha: str = None, observaciones: str = "") -> Tuple[bool, str]:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        products = conn.execute("SELECT id, stock FROM productos").fetchall()
        for p in products:
            conn.execute("""
                INSERT OR REPLACE INTO snapshots_inventario (fecha, producto_id, stock_cierre) 
                VALUES (?, ?, ?)
            """, (fecha, p["id"], float(p["stock"])))
            
        conn.execute("""
            INSERT INTO cierres_inventario (fecha, total_movimientos, total_productos, observaciones)
            SELECT ?, COUNT(*), ?, ? FROM movimientos WHERE fecha LIKE ?
        """, (fecha, len(products), observaciones, f"{fecha}%"))
    return True, f"✅ Cierre guardado. El stock final de hoy será el INV. INI de mañana."