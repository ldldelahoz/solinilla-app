import os
import psycopg2
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL")
IS_LOCAL = DATABASE_URL is None

def get_conn():
    if IS_LOCAL:
        conn = sqlite3.connect("inventario.db")
        conn.row_factory = sqlite3.Row
        return conn
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Tabla USUARIOS
        if IS_LOCAL:
            cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password_hash TEXT, 
                rol TEXT DEFAULT 'usuario')""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY, 
                username TEXT UNIQUE, 
                password_hash TEXT, 
                rol TEXT DEFAULT 'usuario')""")
        
        # Tabla PRODUCTOS
        cur.execute("""CREATE TABLE IF NOT EXISTS productos (
            id TEXT PRIMARY KEY, 
            nombre TEXT NOT NULL, 
            stock REAL DEFAULT 0, 
            fecha_vencimiento TEXT)""")
        
        # Tabla MOVIMIENTOS
        if IS_LOCAL:
            cur.execute("""CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                producto_id TEXT REFERENCES productos(id), 
                tipo TEXT, 
                cantidad REAL, 
                motivo TEXT, 
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS movimientos (
                id SERIAL PRIMARY KEY, 
                producto_id TEXT REFERENCES productos(id) ON DELETE CASCADE, 
                tipo TEXT, 
                cantidad REAL, 
                motivo TEXT, 
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        # Tabla CIERRES DE INVENTARIO
        if IS_LOCAL:
            cur.execute("""CREATE TABLE IF NOT EXISTS cierres_inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                producto_id TEXT NOT NULL,
                inv_ini REAL DEFAULT 0,
                entra REAL DEFAULT 0,
                ventas REAL DEFAULT 0,
                bajas REAL DEFAULT 0,
                inv_final REAL DEFAULT 0,
                observaciones TEXT,
                creado_por TEXT,
                fecha_cierre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fecha, producto_id))""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS cierres_inventario (
                id SERIAL PRIMARY KEY,
                fecha TEXT NOT NULL,
                producto_id TEXT NOT NULL REFERENCES productos(id),
                inv_ini REAL DEFAULT 0,
                entra REAL DEFAULT 0,
                ventas REAL DEFAULT 0,
                bajas REAL DEFAULT 0,
                inv_final REAL DEFAULT 0,
                observaciones TEXT,
                creado_por TEXT,
                fecha_cierre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fecha, producto_id))""")
        
        conn.commit()
        print(f"✅ DB inicializada ({'Neon' if not IS_LOCAL else 'SQLite'})")
        return True
    except Exception as e:
        print(f"❌ Error DB: {e}")
        return False
    finally:
        cur.close()
        conn.close()