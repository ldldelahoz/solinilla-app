#!/usr/bin/env python3
"""
Operaciones de inventario: usuarios, productos, movimientos y cierres diarios.
Compatible con SQLite (local) y PostgreSQL (Render/Neon).
"""

from src.db import get_conn, IS_LOCAL
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# ==========================================
#  USUARIOS
# ==========================================

def obtener_usuario_por_username(username: str) -> Optional[Dict[str, Any]]:
    """Busca un usuario por su nombre de usuario."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("SELECT username, password_hash, rol FROM usuarios WHERE username = ?", (username,))
        else:
            cur.execute("SELECT username, password_hash, rol FROM usuarios WHERE username = %s", (username,))
        
        user = cur.fetchone()
        if user:
            # ✅ CORRECCIÓN: Usar zip() funciona tanto en SQLite como en PostgreSQL
            return dict(zip(['username', 'password_hash', 'rol'], user))
        return None
    except Exception as e:
        print(f"❌ Error obteniendo usuario: {e}")
        return None
    finally:
        cur.close()
        conn.close()


# ==========================================
# 📦 PRODUCTOS
# ==========================================

def obtener_productos() -> List[Dict[str, Any]]:
    """Obtiene todos los productos ordenados por nombre."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre, stock, fecha_vencimiento FROM productos ORDER BY nombre")
        rows = cur.fetchall()
        cols = ['id', 'nombre', 'stock', 'fecha_vencimiento']
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"❌ Error obteniendo productos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def crear_producto(id_prod: str, nombre: str, stock: float = 0.0, fecha_vencimiento: Optional[str] = None) -> tuple:
    """Crea un nuevo producto."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("INSERT INTO productos (id, nombre, stock, fecha_vencimiento) VALUES (?, ?, ?, ?)",
                       (id_prod, nombre, stock, fecha_vencimiento))
        else:
            cur.execute("INSERT INTO productos (id, nombre, stock, fecha_vencimiento) VALUES (%s, %s, %s, %s)",
                       (id_prod, nombre, stock, fecha_vencimiento))
        conn.commit()
        return True, "✅ Producto creado"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        cur.close()
        conn.close()

def eliminar_producto(id_prod: str) -> tuple:
    """Elimina un producto por su ID."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
        else:
            cur.execute("DELETE FROM productos WHERE id = %s", (id_prod,))
        conn.commit()
        return cur.rowcount > 0, "✅ Producto eliminado" if cur.rowcount > 0 else "❌ Producto no encontrado"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        cur.close()
        conn.close()


# ==========================================
# 🔄 MOVIMIENTOS
# ==========================================

def registrar_movimiento(producto_id: str, tipo: str, cantidad: float, motivo: Optional[str] = None) -> tuple:
    """Registra entrada o salida y actualiza el stock automáticamente."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
        else:
            cur.execute("SELECT stock FROM productos WHERE id = %s", (producto_id,))
        
        prod = cur.fetchone()
        if not prod:
            return False, "❌ Producto no encontrado"
        
        stock_actual = prod[0] if IS_LOCAL else prod['stock']
        
        if tipo == "entrada":
            nuevo_stock = stock_actual + cantidad
        elif tipo == "salida":
            nuevo_stock = stock_actual - cantidad
            if nuevo_stock < 0:
                return False, "❌ Stock insuficiente"
        else:
            return False, "❌ Tipo de movimiento inválido"
        
        if IS_LOCAL:
            cur.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, producto_id))
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (?, ?, ?, ?)",
                       (producto_id, tipo, cantidad, motivo))
        else:
            cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (%s, %s, %s, %s)",
                       (producto_id, tipo, cantidad, motivo))
        
        conn.commit()
        return True, f"✅ Movimiento registrado. Nuevo stock: {nuevo_stock}"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {str(e)}"
    finally:
        cur.close()
        conn.close()

def obtener_movimientos_dia(fecha: str) -> List[Dict[str, Any]]:
    """Obtiene todos los movimientos de una fecha específica."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("""SELECT m.id, m.producto_id, m.tipo, m.cantidad, m.motivo, m.fecha 
                          FROM movimientos m WHERE DATE(m.fecha) = DATE(?) ORDER BY m.fecha DESC""", (fecha,))
        else:
            cur.execute("""SELECT m.id, m.producto_id, m.tipo, m.cantidad, m.motivo, m.fecha 
                          FROM movimientos m WHERE DATE(m.fecha) = DATE(%s) ORDER BY m.fecha DESC""", (fecha,))
        
        rows = cur.fetchall()
        cols = ['id', 'producto_id', 'tipo', 'cantidad', 'motivo', 'fecha']
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"❌ Error obteniendo movimientos: {e}")
        return []
    finally:
        cur.close()
        conn.close()


# ==========================================
# 🔒 CIERRES DE INVENTARIO
# ==========================================

def obtener_cierre_anterior(producto_id: str, fecha_actual: str) -> Optional[Dict[str, Any]]:
    """Obtiene el último cierre registrado para un producto."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("""SELECT * FROM cierres_inventario 
                          WHERE producto_id = ? AND fecha <= ? ORDER BY fecha DESC LIMIT 1""", (producto_id, fecha_actual))
        else:
            cur.execute("""SELECT * FROM cierres_inventario 
                          WHERE producto_id = %s AND fecha <= %s ORDER BY fecha DESC LIMIT 1""", (producto_id, fecha_actual))
        
        cierre = cur.fetchone()
        if cierre:
            cols = ['id','fecha','producto_id','inv_ini','entra','ventas','bajas','inv_final','observaciones','creado_por','fecha_cierre']
            return dict(zip(cols, cierre))
        return None
    except Exception as e:
        print(f"❌ Error obteniendo cierre anterior: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def cerrar_inventario_dia(fecha: str, productos_con_datos: List[Dict[str, Any]], creado_por: str = "admin") -> tuple:
    """Guarda un snapshot del inventario para una fecha específica."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("SELECT COUNT(*) FROM cierres_inventario WHERE fecha = ?", (fecha,))
        else:
            cur.execute("SELECT COUNT(*) FROM cierres_inventario WHERE fecha = %s", (fecha,))
        
        if cur.fetchone()[0] > 0:
            return False, f"⚠️ Ya existe un cierre para la fecha {fecha}"
        
        count = 0
        for prod in productos_con_datos:
            if IS_LOCAL:
                cur.execute("""INSERT INTO cierres_inventario 
                    (fecha, producto_id, inv_ini, entra, ventas, bajas, inv_final, observaciones, creado_por)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fecha, prod['producto_id'], prod.get('inv_ini', 0), prod.get('entra', 0),
                     prod.get('ventas', 0), prod.get('bajas', 0), prod.get('inv_final', 0),
                     prod.get('observaciones', ''), creado_por))
            else:
                cur.execute("""INSERT INTO cierres_inventario 
                    (fecha, producto_id, inv_ini, entra, ventas, bajas, inv_final, observaciones, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (fecha, prod['producto_id'], prod.get('inv_ini', 0), prod.get('entra', 0),
                     prod.get('ventas', 0), prod.get('bajas', 0), prod.get('inv_final', 0),
                     prod.get('observaciones', ''), creado_por))
            count += 1
            
        conn.commit()
        return True, f"✅ Inventario cerrado: {count} productos registrados para {fecha}"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error al cerrar inventario: {str(e)}"
    finally:
        cur.close()
        conn.close()

def obtener_cierre_por_fecha(fecha: str) -> List[Dict[str, Any]]:
    """Obtiene todos los productos cerrados en una fecha específica."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("""SELECT c.*, p.nombre FROM cierres_inventario c
                          JOIN productos p ON c.producto_id = p.id WHERE c.fecha = ? ORDER BY p.nombre""", (fecha,))
        else:
            cur.execute("""SELECT c.*, p.nombre FROM cierres_inventario c
                          JOIN productos p ON c.producto_id = p.id WHERE c.fecha = %s ORDER BY p.nombre""", (fecha,))
        
        rows = cur.fetchall()
        cols = ['id','fecha','producto_id','inv_ini','entra','ventas','bajas','inv_final','observaciones','creado_por','fecha_cierre','nombre']
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"❌ Error obteniendo cierre por fecha: {e}")
        return []
    finally:
        cur.close()
        conn.close()