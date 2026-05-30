#!/usr/bin/env python3
"""Script para cargar todos los productos del restaurante Solinilla."""

import sqlite3
from src.db import init_db, DB_PATH

# Lista completa de productos según tu hoja de inventario
PRODUCTOS = [
    # BEBIDAS
    ("SODA HADSU", "Bebidas", None),
    ("COACOLAPET 250ML", "Bebidas", None),
    ("GINGER DRY 300ML", "Bebidas", None),
    ("COCA COLA PET 400", "Bebidas", None),
    ("POSTOBON PET 400", "Bebidas", None),
    ("COCA COLA ZERO 400", "Bebidas", None),
    ("GATORADE", "Bebidas", None),
    ("CERVEZA AGUILA LIGHT", "Bebidas", None),
    ("CERVEZA AGUILA NEGRA", "Bebidas", None),
    ("CERVEZA CLUB COLOMBIA", "Bebidas", None),
    ("CERVEZA STELLA", "Bebidas", None),
    ("AGUA PET 600", "Bebidas", None),
    ("TE HATSU 500 ML", "Bebidas", None),
    ("CERVEZA CORONA 330ML", "Bebidas", None),
    ("SODA SCHWEPPERS", "Bebidas", None),
    
    # RON Y VINOS
    ("AGUARDIENTE 375", "Licores", None),
    ("AGUARDIENTE 750", "Licores", None),
    ("BUCHANNA 375", "Licores", None),
    ("BUCHANNA 750", "Licores", None),
    ("OLD PARR 750", "Licores", None),
    ("RON CALDAS 375", "Licores", None),
    ("RON MEDELLIN 375", "Licores", None),
    ("RON MEDELLIN 750", "Licores", None),
    ("TEQUILA JOSE CUERVO 750", "Licores", None),
    ("TRIPLESECC", "Licores", None),
    ("V.BLANCO S.B SANTA RITA 750", "Licores", None),
    ("V.TINTO C.B 750 SANT RITA", "Licores", None),
    ("V.TINTO POLERO 750ML", "Licores", None),
    
    # PULPAS Y FRUTAS
    ("PULPA DE FRESA 90GR", "Pulpas", None),
    ("PULPA DE MANGO 90 GR", "Pulpas", None),
    ("PULPA DE MARACUYA 90 GR", "Pulpas", None),
    ("PULPA LULO 90 GR", "Pulpas", None),
    ("PULPA DE MORA 90 GR", "Pulpas", None),
    ("PULPA GUANABANA 90 GR", "Pulpas", None),
    ("PULPA DE COROZO KL", "Pulpas", None),
    ("LIMON", "Frutas", None),
    ("NARANJA", "Frutas", None),
    
    # HELADOS Y POSTRES
    ("CHOCO CONO", "Postres", None),
    ("HELADO DE GALLETA", "Postres", None),
    ("PALETA CHOCO BREACK", "Postres", None),
    ("HELADO CASERO", "Postres", None),
    ("POSTRES DE LA CASA", "Postres", None),
    ("CREMA DE COCO", "Postres", None),
    ("CEREZA", "Postres", None),
    ("CREMA DE LECHE", "Postres", None),
    ("V.BLANCO POLERO", "Postres", None),
    ("AZUCAR POR KILO", "Insumos", None),
    ("CAFÉ POR SOBRE", "Insumos", None),
]

def cargar_productos():
    """Carga todos los productos en la base de datos."""
    
    # Inicializar BD
    print("🔧 Inicializando base de datos...")
    init_db()
    print("✅ Tablas listas")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cantidad_cargados = 0
    
    print(f"\n📦 Cargando {len(PRODUCTOS)} productos...\n")
    
    for nombre, categoria, vencimiento in PRODUCTOS:
        try:
            # Generar ID único basado en el nombre
            id_prod = nombre.replace(" ", "_").upper()[:20]
            
            cursor.execute("""
                INSERT OR REPLACE INTO productos (id, nombre, stock, fecha_vencimiento)
                VALUES (?, ?, 0, ?)
            """, (id_prod, nombre, vencimiento))
            
            cantidad_cargados += 1
            print(f"  ✅ {nombre}")
            
        except Exception as e:
            print(f"  ❌ Error con {nombre}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ ¡LISTO! Se cargaron {cantidad_cargados} productos")
    print(f"{'='*60}\n")
    print("🎉 Ahora puedes:")
    print("   1. Iniciar la app: uvicorn main:app --reload")
    print("   2. Entrar a: http://localhost:8000")
    print("   3. Ver todos tus productos en el dashboard")
    print("   4. Registrar inventario inicial")
    print("   5. Generar reportes PDF\n")

if __name__ == "__main__":
    cargar_productos()