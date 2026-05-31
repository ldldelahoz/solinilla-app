from src.db import get_conn, IS_LOCAL, init_db

def cargar_productos():
    """Carga todos los productos del restaurante Solinilla."""
    
    # 1. Primero asegurar que las tablas existen
    print("🔄 Inicializando base de datos...")
    init_db()
    print("✅ Tablas listas. Cargando productos...")
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Lista completa de productos según tu inventario
    productos = [
        # BEBIDAS
        ("1", "SODA HADSU", 20), ("2", "COCACOLAPET 250ML", 50), ("3", "GINGER DRY 300ML", 30),
        ("4", "COCA COLA PET 400", 50), ("5", "POSTOBON PET 400", 40), ("6", "COCA COLA ZERO 400", 30),
        ("7", "GATORADE", 30), ("8", "CERVEZA AGUILA LIGHT", 40), ("9", "CERVEZA AGUILA NEGRA", 40),
        ("10", "CERVEZA CLUB COLOMBIA", 40), ("11", "CERVEZA STELLA", 30), ("12", "AGUA PET 600", 100),
        ("13", "TE HATSU 500 ML", 30), ("14", "CERVEZA CORONA 330ML", 30), ("15", "SODA SCHWEPPERS", 20),
        
        # RON Y VINOS
        ("16", "AGUARDIENTE 375", 20), ("17", "AGUARDIENTE 750", 15), ("18", "BUCHANNA 375", 15),
        ("19", "BUCHANNA 750", 10), ("20", "OLD PARR 750", 10), ("21", "RON CALDAS 375", 15),
        ("22", "RON MEDELLIN 375", 15), ("23", "RON MEDELLIN 750", 10), ("24", "TEQUILA JOSE CUERVO 750", 10),
        ("25", "TRIPLESECC", 10), ("26", "V.BLANCO S.B SANTA RITA 750", 15),
        ("27", "V.TINTO C.B 750 SANT RITA", 15), ("28", "V.TINTO POLERO 750ML", 15),
        
        # PULPAS Y FRUTAS
        ("29", "PULPA DE FRESA 90GR", 30), ("30", "PULPA DE MANGO 90 GR", 30),
        ("31", "PULPA DE MARACUYA 90 GR", 30), ("32", "PULPA LULO 90 GR", 30),
        ("33", "PULPA DE MORA 90 GR", 30), ("34", "PULPA GUANABANA 90 GR", 30),
        ("35", "PULPA DE COROZO KL", 20), ("36", "LIMON", 50), ("37", "NARANJA", 40),
        
        # HELADOS Y POSTRES
        ("38", "CHOCO CONO", 40), ("39", "HELADO DE GALLETA", 30), ("40", "PALETA CHOCO BREACK", 30),
        ("41", "HELADO CASERO", 20), ("42", "POSTRES DE LA CASA", 20), ("43", "CREMA DE COCO", 15),
        ("44", "CEREZA", 15), ("45", "CREMA DE LECHE", 15), ("46", "V.BLANCO POLERO", 15),
        ("47", "AZUCAR POR KILO", 20), ("48", "CAFÉ POR SOBRE", 100)
    ]
    
    count = 0
    try:
        for p in productos:
            pid, nombre, stock = p
            if not IS_LOCAL:
                cur.execute("""
                    INSERT INTO productos (id, nombre, stock) VALUES (%s, %s, %s) 
                    ON CONFLICT (id) DO NOTHING
                """, (pid, nombre, stock))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO productos (id, nombre, stock) VALUES (?, ?, ?)
                """, (pid, nombre, stock))
            count += 1
            
        conn.commit()
        print(f"\n{'='*60}")
        print(f"✅ ¡PRODUCTOS CARGADOS EXITOSAMENTE!")
        print(f"{'='*60}")
        print(f"📦 Total cargado: {count} productos")
        print(f"📋 Categorías:")
        print(f"   🥤 Bebidas: 15")
        print(f"   🍷 Ron y Vinos: 13")
        print(f"   🍓 Pulpa y Frutas: 9")
        print(f"   🍦 Helados y Postres: 11")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error al cargar: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    cargar_productos()