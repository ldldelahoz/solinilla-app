#!/usr/bin/env python3
"""Módulo de conexión a base de datos (PostgreSQL para producción / SQLite para desarrollo)."""

import os
import sys

# === DETECCIÓN AUTOMÁTICA DE BASE DE DATOS ===
DATABASE_URL = os.getenv("DATABASE_URL")

# Si DATABASE_URL existe → Usar PostgreSQL (Neon/Render)
# Si no existe → Usar SQLite local
if DATABASE_URL:
    DB_TYPE = "postgres"
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("❌ Error: psycopg2 no está instalado. Ejecuta: pip install psycopg2-binary")
        sys.exit(1)
else:
    DB_TYPE = "sqlite"
    import sqlite3


def get_conn():
    """
    Obtiene una conexión a la base de datos.
    
    Returns:
        Conexión a PostgreSQL o SQLite según configuración.
    """
    if DB_TYPE == "postgres":
        # PostgreSQL con RealDictCursor para obtener resultados como diccionarios
        return psycopg2.connect(DATABASE_URL)
    else:
        # SQLite local con row_factory para comportamiento similar a dict
        conn = sqlite3.connect("inventario.db")
        conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
        return conn


def get_cursor(conn):
    """
    Obtiene un cursor compatible con el tipo de base de datos.
    
    Args:
        conn: Conexión activa a la base de datos.
    
    Returns:
        Cursor configurado para PostgreSQL o SQLite.
    """
    if DB_TYPE == "postgres":
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()


def init_db():
    """
    Crea las tablas si no existen en la base de datos.
    Compatible con PostgreSQL y SQLite.
    
    Returns:
        bool: True si éxito, False si error.
    """
    conn = get_conn()
    cur = get_cursor(conn)
    
    try:
        if DB_TYPE == "postgres":
            # === TABLA PRODUCTOS (PostgreSQL) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    stock REAL NOT NULL DEFAULT 0,
                    fecha_vencimiento TEXT
                )
            """)
            
            # === TABLA USUARIOS (PostgreSQL) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'usuario',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === TABLA MOVIMIENTOS (PostgreSQL) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id SERIAL PRIMARY KEY,
                    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
                    cantidad REAL NOT NULL CHECK (cantidad > 0),
                    motivo TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === ÍNDICES PARA MEJORAR CONSULTAS ===
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos(producto_id)")
            
        else:
            # === TABLA PRODUCTOS (SQLite) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    stock REAL NOT NULL DEFAULT 0,
                    fecha_vencimiento TEXT
                )
            """)
            
            # === TABLA USUARIOS (SQLite) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'usuario',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === TABLA MOVIMIENTOS (SQLite) ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
                    cantidad REAL NOT NULL CHECK (cantidad > 0),
                    motivo TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === ÍNDICES PARA MEJORAR CONSULTAS ===
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos(producto_id)")
        
        conn.commit()
        print(f"✅ init_db() completado - Usando: {DB_TYPE.upper()}")
        return True
        
    except Exception as e:
        print(f"❌ Error en init_db: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def test_connection():
    """
    Prueba la conexión a la base de datos.
    
    Returns:
        dict: Información sobre la conexión.
    """
    try:
        conn = get_conn()
        cur = get_cursor(conn)
        
        if DB_TYPE == "postgres":
            cur.execute("SELECT current_database(), current_user, version()")
            info = cur.fetchone()
            result = {
                "status": "connected",
                "db_type": "postgres",
                "database": info[0],
                "user": info[1],
                "version": info[2][:50] + "..." if info[2] else "N/A"
            }
        else:
            cur.execute("SELECT sqlite_version()")
            info = cur.fetchone()
            result = {
                "status": "connected",
                "db_type": "sqlite",
                "database": "inventario.db",
                "version": info[0] if info else "N/A"
            }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "db_type": DB_TYPE,
            "error": str(e)
        }
        
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()


def get_db_info():
    """
    Retorna información útil sobre la configuración de la base de datos.
    
    Returns:
        dict: Información de configuración.
    """
    return {
        "db_type": DB_TYPE,
        "using_neon": DB_TYPE == "postgres" and "neon" in (DATABASE_URL or "").lower(),
        "database_url_set": bool(DATABASE_URL),
        "database_url_preview": (DATABASE_URL[:30] + "..." if DATABASE_URL else None)
    }