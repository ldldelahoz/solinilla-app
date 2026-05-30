import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
DB_PATH = Path("data/solinilla.db")

def get_conn():
    """Obtiene conexión a SQLite con configuración optimizada."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    conn.execute("PRAGMA foreign_keys = ON;")  # Integridad referencial
    conn.execute("PRAGMA journal_mode=WAL;")   # Mejor rendimiento y menos bloqueos
    return conn

def init_db():
    """Crea las tablas necesarias si no existen."""
    with get_conn() as conn:
                conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('admin', 'usuario')),
                creado_en TEXT DEFAULT (datetime('now','localtime'))
            );
            
            CREATE TABLE IF NOT EXISTS productos (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                stock REAL NOT NULL DEFAULT 0,
                fecha_vencimiento TEXT
            );
            
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'salida')),
                cantidad REAL NOT NULL,
                motivo TEXT,
                fecha TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS snapshots_inventario (
                fecha TEXT NOT NULL,
                producto_id TEXT NOT NULL,
                stock_cierre REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (fecha, producto_id),
                FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS cierres_inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                total_movimientos INTEGER,
                total_productos INTEGER,
                observaciones TEXT,
                creado_en TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        