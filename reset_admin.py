#!/usr/bin/env python3
"""Script para inicializar BD y resetear la contraseña del usuario admin."""

import sqlite3
from src.auth import hash_password
from src.db import init_db, DB_PATH

def reset_admin_password(new_password: str = "Admin2026!"):
    """Inicializa la BD y crea/actualiza el usuario admin."""
    
    # PASO 1: Inicializar la base de datos (crear tablas)
    print("🔧 Inicializando base de datos...")
    init_db()
    print("✅ Tablas creadas correctamente")
    
    # PASO 2: Crear o actualizar el usuario admin
    print(f"🔐 Configurando usuario admin...")
    hashed = hash_password(new_password)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Intentar actualizar si existe
        cursor.execute("""
            UPDATE usuarios 
            SET password_hash = ?, rol = 'admin'
            WHERE username = 'admin'
        """, (hashed,))
        
        # Si no existe, crearlo
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO usuarios (username, password_hash, rol) 
                VALUES (?, ?, 'admin')
            """, ('admin', hashed))
            print(f"✅ Usuario 'admin' CREADO con contraseña: {new_password}")
        else:
            print(f"✅ Usuario 'admin' ACTUALIZADO con contraseña: {new_password}")
        
        conn.commit()
        print("\n🎉 ¡Listo! Ya puedes hacer login con:")
        print(f"   👤 Usuario: admin")
        print(f"   🔑 Contraseña: {new_password}")
        print(f"\n📁 Base de datos: {DB_PATH}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_admin_password()