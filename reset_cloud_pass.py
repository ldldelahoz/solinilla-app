import psycopg2
import os
from passlib.context import CryptContext

# Pega aquí tu DATABASE_URL de Neon (la misma que usaste para migrar)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:pass@ep-xxxxx.aws.neon.tech/neondb?sslmode=require")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
hashed = pwd_context.hash("Admin2026!")

print("🔄 Conectando a la nube para actualizar contraseña...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Forzar actualización del hash en la tabla usuarios
cur.execute("UPDATE usuarios SET password_hash = %s WHERE username = %s", (hashed, "admin"))
conn.commit()

if cur.rowcount > 0:
    print("✅ ¡Listo! Contraseña de 'admin' actualizada en la nube.")
else:
    print("⚠️ Usuario admin no encontrado. Creándolo...")
    cur.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (%s, %s, %s)", ("admin", hashed, "admin"))
    conn.commit()
    print("✅ Usuario admin creado en la nube.")

conn.close()