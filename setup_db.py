#!/usr/bin/env python3
"""Script completo para crear BD, cargar productos y configurar admin."""
import sqlite3
import os
from passlib.context import CryptContext

DB_PATH = "inventario.db"

# 1️⃣ Limpiar BD anterior para evitar conflictos
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️ Base de datos anterior eliminada.")

print("🔨 Creando nueva base de datos...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 2️⃣ Crear tablas (estructura exacta que espera tu API)
c.execute('''CREATE TABLE productos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    stock REAL NOT NULL DEFAULT 0,
    fecha_vencimiento TEXT
)''')

c.execute('''CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'usuario'
)''')

c.execute('''CREATE TABLE movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    cantidad REAL NOT NULL,
    motivo TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

print("✅ Tablas creadas: productos, usuarios, movimientos")

# 3️⃣ Lista de productos (de tu foto)
PRODUCTOS = [
    "SODA HADSU", "COACOLAPET 250ML", "GINGER DRY 300ML", "COCA COLA PET 400",
    "POSTOBON PET 400", "COCA COLA ZERO 400", "GATORADE", "CERVEZA AGUILA LIGHT",
    "CERVEZA AGUILA NEGRA", "CERVEZA CLUB COLOMBIA", "CERVEZA STELLA", "AGUA PET 600",
    "TE HATSU 500 ML", "CERVEZA CORONA 330ML", "SODA SCHWEPPERS",
    "AGUARDIENTE 375", "AGUARDIENTE 750", "BUCHANNA 375", "BUCHANNA 750",
    "OLD PARR 750", "RON CALDAS 375", "RON MEDELLIN 375", "RON MEDELLIN 750",
    "TEQUILA JOSE CUERVO 750", "TRIPLESECC", "V.BLANCO S.B SANTA RITA 750",
    "V.TINTO C.B 750 SANT RITA", "V.TINTO POLERO 750ML",
    "PULPA DE FRESA 90GR", "PULPA DE MANGO 90 GR", "PULPA DE MARACUYA 90 GR",
    "PULPA LULO 90 GR", "PULPA DE MORA 90 GR", "PULPA GUANABANA 90 GR",
    "PULPA DE COROZO KL", "LIMON", "NARANJA",
    "CHOCO CONO", "HELADO DE GALLETA", "PALETA CHOCO BREACK", "HELADO CASERO",
    "POSTRES DE LA CASA", "CREMA DE COCO", "CEREZA", "CREMA DE LECHE",
    "V.BLANCO POLERO", "AZUCAR POR KILO", "CAFÉ POR SOBRE"
]

print(f"\n📦 Cargando {len(PRODUCTOS)} productos...")
for nombre in PRODUCTOS:
    # Generar ID único limpio
    id_prod = nombre.replace(" ", "_").replace(".", "").upper()[:20]
    c.execute("INSERT OR IGNORE INTO productos (id, nombre, stock) VALUES (?, ?, 0)", 
              (id_prod, nombre))

print("✅ Productos cargados.")

# 4️⃣ Crear usuario admin con hash seguro (PBKDF2)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
hashed_pwd = pwd_context.hash("Admin2026!")
c.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?, ?, 'admin')",
          ("admin", hashed_pwd))
print("✅ Usuario admin creado (admin / Admin2026!)")

conn.commit()
conn.close()

print("\n" + "="*50)
print("🎉 ¡BASE DE DATOS LISTA!")
print("="*50)
print(" Ahora ejecuta: uvicorn main:app --reload")
print("👉 Abre: http://localhost:8000")
print("👉 Login: admin / Admin2026!")