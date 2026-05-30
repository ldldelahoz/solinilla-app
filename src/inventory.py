#!/usr/bin/env python3
"""Módulo de operaciones de inventario y usuarios."""

from datetime import datetime
from src.db import get_conn, DB_TYPE

# === USUARIOS ===

def obtener_usuario_por_username(username: str):
    """Obtiene un usuario desde la base de datos por su nombre de usuario."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if DB_TYPE == "postgres":
            query = "SELECT id, username, password_hash, rol FROM usuarios WHERE username = %s"
            cur.execute(query, (username,))
        else:
            query = "SELECT id, username, password_hash, rol FROM usuarios WHERE username = ?"
            cur.execute(query, (username,))
        
        user = cur.fetchone()
        if user:
            # Manejar tanto dict (PostgreSQL con RealDictCursor) como tuple (SQLite)
            if hasattr(user, 'keys'):  # psycopg2 RealDictCursor
                return dict(user)
            else:  # sqlite3 Row o tuple
                return {
                    'id': user[0],
                    'username': user[1],
                    'password_hash': user[2],
                    'rol': user[3]
                }
        return None
    except Exception as e:
        print(f"❌ Error obteniendo usuario: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# === PRODUCTOS ===

def obtener_productos():
    """Obtiene todos los productos de la base de datos."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        query = "SELECT id, nombre, stock, fecha_vencimiento FROM productos ORDER BY nombre"
        cur.execute(query)
        rows = cur.fetchall()
        
        # Convertir a lista de diccionarios
        if DB_TYPE == "postgres":
            return [dict(row) for row in rows]
        else:
            # SQLite: crear diccionarios manualmente
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Error obteniendo productos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def crear_producto(id_prod: str, nombre: str, stock: float = 0, fecha_vencimiento: str = None):
    """Crea un nuevo producto en la base de datos."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if DB_TYPE == "postgres":
            query = """
                INSERT INTO productos (id, nombre, stock, fecha_vencimiento) 
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(query, (id_prod, nombre, stock, fecha_vencimiento))
        else:
            query = """
                INSERT INTO productos (id, nombre, stock, fecha_vencimiento) 
                VALUES (?, ?, ?, ?)
            """
            cur.execute(query, (id_prod, nombre, stock, fecha_vencimiento))
        
        conn.commit()
        return True, "✅ Producto creado"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {e}"
    finally:
        cur.close()
        conn.close()

def eliminar_producto(id_prod: str):
    """Elimina un producto de la base de datos."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if DB_TYPE == "postgres":
            query = "DELETE FROM productos WHERE id = %s"
            cur.execute(query, (id_prod,))
        else:
            query = "DELETE FROM productos WHERE id = ?"
            cur.execute(query, (id_prod,))
        
        conn.commit()
        if cur.rowcount > 0:
            return True, "✅ Producto eliminado"
        return False, "❌ Producto no encontrado"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {e}"
    finally:
        cur.close()
        conn.close()

# === MOVIMIENTOS ===

def registrar_movimiento(id_prod: str, tipo: str, cantidad: float, motivo: str = None):
    """Registra un movimiento (entrada/salida) y actualiza el stock."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        # 1. Verificar que el producto existe y obtener stock actual
        if DB_TYPE == "postgres":
            cur.execute("SELECT stock FROM productos WHERE id = %s", (id_prod,))
        else:
            cur.execute("SELECT stock FROM productos WHERE id = ?", (id_prod,))
        
        producto = cur.fetchone()
        if not producto:
            return False, "❌ Producto no encontrado"
        
        # Obtener valor de stock (compatible con dict y tuple)
        stock_actual = producto['stock'] if hasattr(producto, 'keys') else producto[0]
        
        # 2. Calcular nuevo stock
        if tipo == "entrada":
            nuevo_stock = stock_actual + cantidad
        elif tipo == "salida":
            nuevo_stock = stock_actual - cantidad
            if nuevo_stock < 0:
                return False, "❌ Stock insuficiente"
        else:
            return False, "❌ Tipo de movimiento inválido"
        
        # 3. Actualizar stock del producto
        if DB_TYPE == "postgres":
            cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id_prod))
            # 4. Registrar el movimiento
            cur.execute(
                "INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (%s, %s, %s, %s)",
                (id_prod, tipo, cantidad, motivo)
            )
        else:
            cur.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id_prod))
            cur.execute(
                "INSERT INTO movimientos (producto_id, tipo, cantidad, motivo) VALUES (?, ?, ?, ?)",
                (id_prod, tipo, cantidad, motivo)
            )
        
        conn.commit()
        return True, f"✅ Movimiento registrado. Nuevo stock: {nuevo_stock}"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Error: {e}"
    finally:
        cur.close()
        conn.close()

def obtener_movimientos_dia(fecha: str):
    """Obtiene todos los movimientos de una fecha específica."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if DB_TYPE == "postgres":
            query = """
                SELECT m.id, m.producto_id, p.nombre, m.tipo, m.cantidad, m.motivo, m.fecha
                FROM movimientos m
                LEFT JOIN productos p ON m.producto_id = p.id
                WHERE DATE(m.fecha) = DATE(%s)
                ORDER BY m.fecha DESC
            """
            cur.execute(query, (fecha,))
        else:
            query = """
                SELECT m.id, m.producto_id, p.nombre, m.tipo, m.cantidad, m.motivo, m.fecha
                FROM movimientos m
                LEFT JOIN productos p ON m.producto_id = p.id
                WHERE DATE(m.fecha) = DATE(?)
                ORDER BY m.fecha DESC
            """
            cur.execute(query, (fecha,))
        
        rows = cur.fetchall()
        
        # Convertir a lista de diccionarios
        if DB_TYPE == "postgres":
            return [dict(row) for row in rows]
        else:
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Error obteniendo movimientos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# === CIERRE DE INVENTARIO ===

def cerrar_inventario_dia(fecha: str, observaciones: str = ""):
    """Registra el cierre del inventario de un día (snapshot)."""
    try:
        # Aquí podrías guardar un snapshot del stock actual en una tabla 'cierres'
        # Por ahora, solo registramos en logs
        print(f"🔒 Cierre de inventario para {fecha}: {observaciones}")
        return True, f"✅ Inventario cerrado para {fecha}"
    except Exception as e:
        return False, f"❌ Error al cerrar: {e}"

# === INICIALIZACIÓN ===

def init_db():
    """Crea las tablas si no existen."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if DB_TYPE == "postgres":
            # Tabla productos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    stock REAL NOT NULL DEFAULT 0,
                    fecha_vencimiento TEXT
                )
            """)
            # Tabla usuarios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'usuario'
                )
            """)
            # Tabla movimientos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id SERIAL PRIMARY KEY,
                    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL,
                    cantidad REAL NOT NULL,
                    motivo TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite fallback
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    stock REAL NOT NULL DEFAULT 0,
                    fecha_vencimiento TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'usuario'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL,
                    cantidad REAL NOT NULL,
                    motivo TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        print(f"✅ init_db() completado ({DB_TYPE})")
        return True
    except Exception as e:
        print(f"❌ Error en init_db: {e}")
        return False
    finally:
        cur.close()
        conn.close()