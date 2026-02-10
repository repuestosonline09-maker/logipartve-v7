# database/migrations/add_quote_numbering.py
# Migración para agregar sistema de numeración automática de cotizaciones

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from database.db_manager import DBManager

def migrate():
    """
    Agrega tabla user_quote_ranges para gestionar rangos de numeración por usuario.
    
    Rangos asignados:
    - Usuario 1 (primer creado): 30000-39999
    - Usuario 2: 40000-49999
    - Usuario 3: 50000-59999
    - Usuario 4: 60000-69999
    - Usuario 5: 70000-79999
    """
    conn = DBManager.get_connection()
    cursor = conn.cursor()
    is_postgres = DBManager.USE_POSTGRES
    id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    try:
        # Crear tabla de rangos de usuarios
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_quote_ranges (
                id {id_type},
                user_id INTEGER UNIQUE NOT NULL,
                range_start INTEGER NOT NULL,
                range_end INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Crear tabla de secuencias de cotizaciones por usuario y año
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS quote_sequences (
                id {id_type},
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                last_number INTEGER NOT NULL,
                UNIQUE(user_id, year),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        print("✅ Tablas de numeración de cotizaciones creadas exitosamente")
        
        # Asignar rangos a usuarios existentes
        cursor.execute("SELECT id, username FROM users ORDER BY id ASC")
        users = cursor.fetchall()
        
        base_ranges = [30000, 40000, 50000, 60000, 70000]
        
        for idx, user in enumerate(users):
            if idx >= len(base_ranges):
                print(f"⚠️ Usuario {user['username']} excede el límite de 5 usuarios")
                continue
            
            user_id = user['id']
            range_start = base_ranges[idx]
            range_end = range_start + 9999
            
            # Verificar si ya tiene rango asignado
            cursor.execute("""
                SELECT COUNT(*) FROM user_quote_ranges WHERE user_id = %s
            """ if is_postgres else """
                SELECT COUNT(*) FROM user_quote_ranges WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            count = result['count'] if is_postgres else result[0]
            
            if count == 0:
                cursor.execute("""
                    INSERT INTO user_quote_ranges (user_id, range_start, range_end)
                    VALUES (%s, %s, %s)
                """ if is_postgres else """
                    INSERT INTO user_quote_ranges (user_id, range_start, range_end)
                    VALUES (?, ?, ?)
                """, (user_id, range_start, range_end))
                
                print(f"✅ Rango {range_start}-{range_end} asignado a usuario '{user['username']}'")
        
        conn.commit()
        print("✅ Migración completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error en migración: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
