import psycopg2
import os

# Obtener URL de la variable de entorno
db_url = os.environ.get('DATABASE_URL')

if not db_url:
    print("❌ No se encontró DATABASE_URL")
    exit()

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Ver duplicados
    print("🔍 Buscando duplicados...")
    cur.execute("SELECT nombre, COUNT(*) FROM productos GROUP BY nombre HAVING COUNT(*) > 1")
    dups = cur.fetchall()
    
    if dups:
        print(f"\n📦 Productos duplicados encontrados:")
        for d in dups:
            print(f"  - {d[0]}: {d[1]} registros")
        
        confirmar = input("\n¿Eliminar duplicados? (s/n): ")
        if confirmar.lower() == 's':
            # Eliminar duplicados
            cur.execute("""
                DELETE FROM productos
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM productos
                    GROUP BY nombre
                )
            """)
            conn.commit()
            print(f"✅ Eliminados {cur.rowcount} productos duplicados")
        else:
            print("❌ Cancelado")
    else:
        print("✅ No hay duplicados")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")