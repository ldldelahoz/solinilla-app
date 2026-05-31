from src.db import get_conn, IS_LOCAL
from datetime import datetime, timedelta
from typing import Optional, List

def obtener_usuario_por_username(username: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("SELECT username, password_hash, rol FROM usuarios WHERE username = ?", (username,))
        else:
            cur.execute("SELECT username, password_hash, rol FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            return dict(user) if not IS_LOCAL else dict(zip(['username','password_hash','rol'], user))
        return None
    except Exception as e:
        print(f"❌ Error usuario: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def obtener_productos():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre, stock, fecha_vencimiento FROM productos ORDER BY nombre")
        rows = cur.fetchall()
        return [dict(row) for row in rows] if not IS_LOCAL else [dict(zip(['id','nombre','stock','fecha_vencimiento'], r)) for r in rows]
    except Exception as e:
        print(f"❌ Error productos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def crear_producto(id_prod: str, nombre: str, stock: float = 0, fecha_vencimiento: str = None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("INSERT INTO productos (id, nombre, stock, fecha_vencimiento) VALUES (?,?,?,?)", 
                       (id_prod, nombre, stock, fecha_vencimiento))
        else:
            cur.execute("INSERT INTO productos (id, nombre, stock, fecha_vencimiento) VALUES (%s,%s,%s,%s)", 
                       (id_prod, nombre, stock, fecha_vencimiento))
        conn.commit()
        return True, "✅ Producto creado"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close()
        conn.close()

def eliminar_producto(id_prod: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
        else:
            cur.execute("DELETE FROM productos WHERE id = %s", (id_prod,))
        conn.commit()
        return cur.rowcount > 0, "✅ Eliminado" if cur.rowcount > 0 else "❌ No encontrado"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close()
        conn.close()

def registrar_movimiento(producto_id: str, tipo: str, cantidad: float, motivo: str = None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
        else:
            cur.execute("SELECT stock FROM productos WHERE id = %s", (producto_id,))
        prod = cur.fetchone()
        if not prod: return False, "❌ Producto no encontrado"
        stock_actual = prod['stock'] if not IS_LOCAL else prod[0]
        nuevo = stock_actual + (cantidad if tipo == 'entrada' else -cantidad)
        if nuevo < 0: return False, "❌ Stock insuficiente"
        
        if IS_LOCAL:
            cur.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo, producto_id))
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (?,?,?,?)", 
                       (producto_id, tipo, cantidad, motivo))
        else:
            cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo, producto_id))
            cur.execute("INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (%s,%s,%s,%s)", 
                       (producto_id, tipo, cantidad, motivo))
        conn.commit()
        return True, f"✅ Stock actualizado: {nuevo}"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close()
        conn.close()

def obtener_movimientos_dia(fecha: str):
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
        return [dict(row) for row in rows] if not IS_LOCAL else [dict(zip(['id','producto_id','tipo','cantidad','motivo','fecha'], r)) for r in rows]
    except Exception as e:
        print(f"❌ Error movimientos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# === NUEVAS FUNCIONES DE CIERRE DE INVENTARIO ===

def obtener_cierre_anterior(producto_id: str, fecha_actual: str) -> Optional[dict]:
    """Obtiene el cierre del día anterior. El inv_final es el inv_ini del día actual."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if IS_LOCAL:
            cur.execute("""SELECT * FROM cierres_inventario 
                          WHERE producto_id = ? AND fecha <= ? ORDER BY fecha DESC LIMIT 1""", 
                       (producto_id, fecha_actual))
        else:
            cur.execute("""SELECT * FROM cierres_inventario 
                          WHERE producto_id = %s AND fecha <= %s ORDER BY fecha DESC LIMIT 1""", 
                       (producto_id, fecha_actual))
        
        cierre = cur.fetchone()
        if cierre:
            if IS_LOCAL:
                return dict(zip(['id','fecha','producto_id','inv_ini','entra','ventas','bajas','inv_final','observaciones','creado_por','fecha_cierre'], cierre))
            else:
                return dict(cierre)
        return None
    except Exception as e:
        print(f"❌ Error obteniendo cierre anterior: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def cerrar_inventario_dia(fecha: str, productos_con_datos: List[dict], creado_por: str = "admin") -> tuple:
    """
    Cierra el inventario de un día. Guarda snapshot de INV INI, ENTRA, VENTAS, BAJAS, INV FINAL.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Verificar si ya existe cierre
        if IS_LOCAL:
            cur.execute("SELECT COUNT(*) FROM cierres_inventario WHERE fecha = ?", (fecha,))
        else:
            cur.execute("SELECT COUNT(*) FROM cierres_inventario WHERE fecha = %s", (fecha,))
        
        if cur.fetchone()[0] > 0:
            return False, f"⚠️ Ya existe cierre para {fecha}"
        
        # Insertar cierre por cada producto
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
        return True, f"✅ Inventario cerrado: {count} productos para {fecha}"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error al cerrar: {str(e)}"
    finally:
        cur.close()
        conn.close()

def obtener_cierre_por_fecha(fecha: str) -> List[dict]:
    """Obtiene todos los productos cerrados en una fecha."""
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
        if IS_LOCAL:
            return [dict(zip(['id','fecha','producto_id','inv_ini','entra','ventas','bajas','inv_final','observaciones','creado_por','fecha_cierre','nombre'], r)) for r in rows]
        else:
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"❌ Error obteniendo cierre: {e}")
        return []
    finally:
        cur.close()
        conn.close()