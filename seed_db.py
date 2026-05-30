"""
Script para cargar productos iniciales del Restaurante Solinilla
Ejecutar: .\.venv\Scripts\python.exe seed_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/solinilla.db")

PRODUCTOS = [
    # BEBIDAS
    ("BEB001", "SODA HADSU", "UND"),
    ("BEB002", "COCA COLA PET 250ML", "UND"),
    ("BEB003", "GINGER DRY 300ML", "UND"),
    ("BEB004", "COCA COLA PET 400ML", "UND"),
    ("BEB005", "POSTOBON PET 400ML", "UND"),
    ("BEB006", "COCA COLA ZERO 400ML", "UND"),
    ("BEB007", "GATORADE", "UND"),
    ("BEB008", "CERVEZA AGUILA LIGHT", "UND"),
    ("BEB009", "CERVEZA AGUILA NEGRA", "UND"),
    ("BEB010", "CERVEZA CLUB COLOMBIA", "UND"),
    ("BEB011", "CERVEZA STELLA", "UND"),
    ("BEB012", "AGUA PET 600ML", "UND"),
    ("BEB013", "TE HATSU 500ML", "UND"),
    ("BEB014", "CERVEZA CORONA 330ML", "UND"),
    ("BEB015", "SODA SCHWEPPERS", "UND"),
    
    # RON Y VINOS
    ("LIC001", "AGUARDIENTE 375ML", "UND"),
    ("LIC002", "AGUARDIENTE 750ML", "UND"),
    ("LIC003", "BUCHANNA 375ML", "UND"),
    ("LIC004", "BUCHANNA 750ML", "UND"),
    ("LIC005", "OLD PARR 750ML", "UND"),
    ("LIC006", "RON CALDAS 375ML", "UND"),
    ("LIC007", "RON MEDELLIN 375ML", "UND"),
    ("LIC008", "RON MEDELLIN 750ML", "UND"),
    ("LIC009", "TEQUILA JOSE CUERVO 750ML", "UND"),
    ("LIC010", "TRIPLE SECC", "UND"),
    ("LIC011", "VINO BLANCO SANTA RITA 750ML", "UND"),
    ("LIC012", "VINO TINTO SANTA RITA 750ML", "UND"),
    ("LIC013", "VINO TINTO POLERO 750ML", "UND"),
    
    # PULPAS Y FRUTAS
    ("FRU001", "PULPA DE FRESA 90GR", "UND"),
    ("FRU002", "PULPA DE MANGO 90GR", "UND"),
    ("FRU003", "PULPA DE MARACUYA 90GR", "UND"),
    ("FRU004", "PULPA DE LULO 90GR", "UND"),
    ("FRU005", "PULPA DE MORA 90GR", "UND"),
    ("FRU006", "PULPA DE GUANABANA 90GR", "UND"),
    ("FRU007", "PULPA DE COROZO KG", "KG"),
    ("FRU008", "LIMON", "KG"),
    ("FRU009", "NARANJA", "KG"),
    
    # HELADOS Y POSTRES
    ("HEL001", "CHOCO CONO", "UND"),
    ("HEL002", "HELADO DE GALLETA", "UND"),
    ("HEL003", "PALETA CHOCO BREAK", "UND"),
    ("HEL004", "HELADO CASERO", "UND"),
    ("HEL005", "POSTRES DE LA CASA", "UND"),
    ("HEL006", "CREMA DE COCO", "UND"),
    ("HEL007", "CEREZA", "UND"),
    ("HEL008", "CREMA DE LECHE", "UND"),
    ("HEL009", "VINO BLANCO POLERO", "UND"),
    
    # VARIOS
    ("VAR001", "AZUCAR POR KILO", "KG"),
    ("VAR002", "CAFE POR SOBRE", "UND"),
]

def cargar_productos():
    if not DB_PATH.exists():
        print("❌ La base de datos no existe. Ejecuta main.py primero.")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    print("🔄 Cargando productos del Restaurante Solinilla...")
    print("="*50)
    
    cargados = 0
    duplicados = 0
    errores = 0
    
    for id_prod, nombre, unidad in PRODUCTOS:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO productos (id, nombre, stock, fecha_vencimiento)
                VALUES (?, ?, 0, NULL)
            """, (id_prod, f"{nombre} ({unidad})",))
            
            if cursor.rowcount > 0:
                print(f"✅ {id_prod}: {nombre}")
                cargados += 1
            else:
                print(f"⏭️  {id_prod}: Ya existe")
                duplicados += 1
                
        except Exception as e:
            print(f"❌ Error con {id_prod}: {e}")
            errores += 1
    
    conn.commit()
    conn.close()
    
    print("="*50)
    print(f"📊 RESUMEN:")
    print(f"   ✅ Cargados: {cargados}")
    print(f"   ⏭️  Duplicados: {duplicados}")
    print(f"   ❌ Errores: {errores}")
    print(f"   📦 Total: {len(PRODUCTOS)} productos")

if __name__ == "__main__":
    cargar_productos()