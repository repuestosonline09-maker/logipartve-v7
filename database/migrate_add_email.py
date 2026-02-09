#!/usr/bin/env python3
"""
Script de migración: Agregar columna 'email' a la tabla users
Ejecutar una sola vez después del deployment
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar DBManager
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DBManager

def migrate_add_email_column():
    """Agrega la columna email a la tabla users si no existe."""
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        if DBManager.USE_POSTGRES:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='email'
            """)
        else:
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] if isinstance(row, tuple) else row['name'] for row in cursor.fetchall()]
            cursor.execute("SELECT 1")  # Reset cursor
        
        result = cursor.fetchone()
        
        if not result:
            print("📝 Agregando columna 'email' a la tabla users...")
            
            if DBManager.USE_POSTGRES:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            else:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            
            conn.commit()
            print("✅ Columna 'email' agregada exitosamente")
        else:
            print("ℹ️  La columna 'email' ya existe en la tabla users")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error en la migración: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Iniciando migración: Agregar columna email")
    migrate_add_email_column()
    print("🎉 Migración completada")
