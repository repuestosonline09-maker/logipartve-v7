#!/usr/bin/env python3
"""
Script para resetear la contraseña del usuario admin
Ejecutar: python3 database/reset_admin_password.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar DBManager
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DBManager
import bcrypt

def reset_admin_password(new_password: str = "Lamesita.99"):
    """Resetea la contraseña del usuario admin."""
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Generar hash de la nueva contraseña
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Actualizar contraseña del admin
        if DBManager.USE_POSTGRES:
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s 
                WHERE username = %s
            """, (password_hash.decode('utf-8'), 'admin'))
        else:
            cursor.execute("""
                UPDATE users 
                SET password_hash = ? 
                WHERE username = ?
            """, (password_hash.decode('utf-8'), 'admin'))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Contraseña del admin reseteada exitosamente a: {new_password}")
        else:
            print("⚠️  Usuario 'admin' no encontrado en la base de datos")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al resetear contraseña: {e}")
        raise

if __name__ == "__main__":
    print("🔐 Reseteando contraseña del usuario admin...")
    reset_admin_password()
    print("🎉 Proceso completado")
