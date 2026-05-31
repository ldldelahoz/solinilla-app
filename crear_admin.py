from src.db import get_conn, IS_LOCAL, init_db
from src.auth import hash_password

def crear_admin():
    """Crea el usuario admin en la base de datos."""
    
    # Primero asegurar que las tablas existen
    print("🔄 Inicializando base de datos...")
    init_db()
    
    conn = get_conn()
    cur = conn.cursor()
    
    username = "admin"
    password = "Admin2026!"
    hashed = hash_password(password)
    
    try:
        if IS_LOCAL:
            cur.execute("""
                INSERT OR REPLACE INTO usuarios (username, password_hash, rol) 
                VALUES (?, ?, ?)
            """, (username, hashed, "admin"))
        else:
            cur.execute("""
                INSERT INTO usuarios (username, password_hash, rol) 
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO UPDATE 
                SET password_hash = EXCLUDED.password_hash, rol = EXCLUDED.rol
            """, (username, hashed, "admin"))
        
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ ¡USUARIO ADMIN CREADO!")
        print(f"{'='*60}")
        print(f"👤 Usuario: {username}")
        print(f"🔑 Contraseña: {password}")
        print(f"🔐 Hash: {hashed[:30]}...")
        print(f"\n🌐 Ahora puedes iniciar sesión en http://127.0.0.1:8000")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    crear_admin()