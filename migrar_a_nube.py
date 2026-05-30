#!/usr/bin/env python3
"""Script para migrar productos de SQLite local a PostgreSQL en la nube."""

import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

# Cargar variables de entorno si tienes .env
load_dotenv()

# 🔹 Configuración LOCAL (SQLite)
LOCAL_DB = "inventario.db"

# 🔹 Configuración NUBE (PostgreSQL - Neon)
# Copia tu DATABASE_URL de Neon y pégala aquí o en variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:pass@ep-xxxxx.aws.neon.tech/neondb?sslmode=require")

def migrar_productos():
    print("🔄 Iniciando migración: SQLite → PostgreSQL\n")
    
    # 1️⃣ Conectar a SQLite local
    print("📁 Conectando a SQLite local...")
    local_conn = sqlite3.connect(LOCAL_DB)
    local_cur = local_conn.cursor()
    
    # 2️⃣ Conectar a PostgreSQL en la nube
    print("☁️ Conectando a PostgreSQL (Neon)...")
    cloud_conn = psycopg2.connect(DATABASE_URL)
    cloud_cur = cloud_conn.cursor()
    
    # 3️⃣ Crear tablas en la nube si no existen
    print("🔨 Creando tablas en la nube...")
    cloud_cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            stock REAL NOT NULL DEFAULT 0,
            fecha_vencimiento TEXT
        )
    """)
    cloud_cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario'
        )
    """)
    cloud_cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,
            cantidad REAL NOT NULL,
            motivo TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cloud_conn.commit()
    print("✅ Tablas listas en la nube")
    
    # 4️⃣ Copiar productos
    print("\n📦 Migrando productos...")
    local_cur.execute("SELECT id, nombre, stock, fecha_vencimiento FROM productos")
    productos = local_cur.fetchall()
    
    migrados = 0
    for prod in productos:
        try:
            cloud_cur.execute("""
                INSERT INTO productos (id, nombre, stock, fecha_vencimiento)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    nombre = EXCLUDED.nombre,
                    stock = EXCLUDED.stock,
                    fecha_vencimiento = EXCLUDED.fecha_vencimiento
            """, prod)
            migrados += 1
            print(f"  ✅ {prod[1]}")
        except Exception as e:
            print(f"  ❌ Error con {prod[1]}: {e}")
    
    cloud_conn.commit()
    
    # 5️⃣ Crear usuario admin en la nube (con PBKDF2)
    print("\n🔐 Configurando admin en la nube...")
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    hashed = pwd_context.hash("Admin2026!")
    
    cloud_cur.execute("""
        INSERT INTO usuarios (username, password_hash, rol)
        VALUES (%s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
    """, ("admin", hashed, "admin"))
    cloud_conn.commit()
    print("✅ Usuario admin configurado (admin / Admin2026!)")
    
    # Cerrar conexiones
    local_conn.close()
    cloud_conn.close()
    
    print(f"\n{'='*60}")
    print(f"🎉 ¡MIGRACIÓN COMPLETADA!")
    print(f"{'='*60}")
    print(f"✅ Productos migrados: {migrados}")
    print(f"✅ Admin configurado en la nube")
    print(f"\n🚀 Ahora haz git push y redeploy en Render")
    print(f"👉 Tu app en la nube tendrá los mismos datos que tu local")

if __name__ == "__main__":
    migrar_productos()