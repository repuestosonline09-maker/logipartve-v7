# database/db_manager.py
# Gestor de base de datos con soporte para SQLite (desarrollo) y PostgreSQL (producción)

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import bcrypt

class DBManager:
    """
    Gestor de base de datos para LogiPartVE Pro v7.0
    Maneja 7 tablas: users, system_config, quotes, quote_items, pages, cache, activity_logs
    Soporta SQLite (desarrollo local) y PostgreSQL (producción en Railway)
    """
    
    DB_PATH = Path(__file__).parent / "logipartve.db"
    USE_POSTGRES = os.getenv("DATABASE_URL") is not None
    
    @staticmethod
    def get_connection():
        """Crea y retorna una conexión a la base de datos (SQLite o PostgreSQL)."""
        if DBManager.USE_POSTGRES:
            # Producción: PostgreSQL en Railway
            database_url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn
        else:
            # Desarrollo: SQLite local
            conn = sqlite3.connect(str(DBManager.DB_PATH))
            conn.row_factory = sqlite3.Row
            return conn
    
    @staticmethod
    def init_database():
        """Inicializa todas las tablas de la base de datos."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Detectar si es PostgreSQL o SQLite para usar sintaxis correcta
        is_postgres = DBManager.USE_POSTGRES
        
        # AUTOINCREMENT en SQLite vs SERIAL en PostgreSQL
        id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        # Tabla 1: users
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {id_type},
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'analyst')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Tabla 2: system_config
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        # Tabla 3: quotes
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS quotes (
                id {id_type},
                quote_number TEXT UNIQUE NOT NULL,
                analyst_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                client_phone TEXT,
                client_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount REAL,
                status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'sent', 'approved', 'rejected')),
                pdf_path TEXT,
                jpeg_path TEXT,
                FOREIGN KEY (analyst_id) REFERENCES users(id)
            )
        """)
        
        # Tabla 4: quote_items
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS quote_items (
                id {id_type},
                quote_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                part_number TEXT,
                quantity INTEGER NOT NULL,
                unit_cost REAL NOT NULL,
                international_handling REAL DEFAULT 0,
                national_handling REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                tax_percentage REAL DEFAULT 0,
                profit_factor REAL DEFAULT 1.25,
                page_url TEXT,
                origin TEXT CHECK(origin IN ('Miami', 'Madrid', 'Manual')),
                FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE
            )
        """)
        
        # Tabla 5: pages
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS pages (
                id {id_type},
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                origin TEXT NOT NULL CHECK(origin IN ('Miami', 'Madrid')),
                active INTEGER DEFAULT 1
            )
        """)
        
        # Tabla 6: cache
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS cache (
                id {id_type},
                part_number TEXT UNIQUE NOT NULL,
                description TEXT,
                unit_cost REAL,
                international_handling REAL,
                national_handling REAL,
                shipping_cost REAL,
                source TEXT,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla 7: activity_logs
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id {id_type},
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tabla 8: freight_rates (tarifas de flete)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS freight_rates (
                id {id_type},
                origin TEXT NOT NULL CHECK(origin IN ('Miami', 'Madrid')),
                shipping_type TEXT NOT NULL CHECK(shipping_type IN ('Aéreo', 'Marítimo')),
                rate REAL NOT NULL,
                unit TEXT NOT NULL,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(id),
                UNIQUE(origin, shipping_type)
            )
        """)
        
        conn.commit()
        
        # Crear usuario admin por defecto si no existe
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        count = result[0] if is_postgres else result[0]
        
        if count == 0:
            admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
            """ if is_postgres else """
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            """, ('admin', admin_password.decode('utf-8'), 'Administrador', 'admin'))
            conn.commit()
        
        cursor.close()
        conn.close()
    
    # ==================== MÉTODOS DE USUARIOS ====================
    
    @staticmethod
    def create_user(username: str, password: str, full_name: str, role: str) -> bool:
        """Crea un nuevo usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
            """ if is_postgres else """
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash.decode('utf-8'), full_name, role))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al crear usuario: {e}")
            return False
    
    @staticmethod
    def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifica las credenciales de un usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT * FROM users WHERE username = %s
            """ if is_postgres else """
                SELECT * FROM users WHERE username = ?
            """, (username,))
            
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # Actualizar last_login
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """ if is_postgres else """
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                """, (user['id'],))
                conn.commit()
                
                cursor.close()
                conn.close()
                return dict(user)
            
            cursor.close()
            conn.close()
            return None
        except Exception as e:
            print(f"Error al verificar usuario: {e}")
            return None
    
    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Obtiene todos los usuarios."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, full_name, role, created_at, last_login FROM users")
            users = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return users
        except Exception as e:
            print(f"Error al obtener usuarios: {e}")
            return []
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Obtiene un usuario por su nombre de usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT * FROM users WHERE username = %s
            """ if is_postgres else """
                SELECT * FROM users WHERE username = ?
            """, (username,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None
    
    @staticmethod
    def update_last_login(user_id: int) -> bool:
        """Actualiza la fecha de último login de un usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
            """ if is_postgres else """
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al actualizar último login: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Elimina un usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                DELETE FROM users WHERE id = %s
            """ if is_postgres else """
                DELETE FROM users WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al eliminar usuario: {e}")
            return False
    
    # ==================== MÉTODOS DE CONFIGURACIÓN ====================
    
    @staticmethod
    def get_config(key: str) -> Optional[str]:
        """Obtiene un valor de configuración."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT value FROM system_config WHERE key = %s
            """ if is_postgres else """
                SELECT value FROM system_config WHERE key = ?
            """, (key,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result['value'] if result else None
        except Exception as e:
            print(f"Error al obtener configuración: {e}")
            return None
    
    @staticmethod
    def set_config(key: str, value: str, description: str = "", updated_by: int = None) -> bool:
        """Establece un valor de configuración."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            
            # Verificar si la clave ya existe
            cursor.execute("""
                SELECT COUNT(*) FROM system_config WHERE key = %s
            """ if is_postgres else """
                SELECT COUNT(*) FROM system_config WHERE key = ?
            """, (key,))
            
            result = cursor.fetchone()
            exists = result[0] if is_postgres else result[0]
            
            if exists > 0:
                # Actualizar
                cursor.execute("""
                    UPDATE system_config SET value = %s, description = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE key = %s
                """ if is_postgres else """
                    UPDATE system_config SET value = ?, description = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (value, description, updated_by, key))
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO system_config (key, value, description, updated_by)
                    VALUES (%s, %s, %s, %s)
                """ if is_postgres else """
                    INSERT INTO system_config (key, value, description, updated_by)
                    VALUES (?, ?, ?, ?)
                """, (key, value, description, updated_by))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al establecer configuración: {e}")
            return False
    
    @staticmethod
    def get_all_config() -> List[Dict[str, Any]]:
        """Obtiene toda la configuración del sistema."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_config")
            config = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return config
        except Exception as e:
            print(f"Error al obtener configuración: {e}")
            return []
    
    # ==================== MÉTODOS DE TARIFAS DE FLETE ====================
    
    @staticmethod
    def get_freight_rate(origin: str, shipping_type: str) -> Optional[float]:
        """Obtiene la tarifa de flete."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT rate FROM freight_rates WHERE origin = %s AND shipping_type = %s
            """ if is_postgres else """
                SELECT rate FROM freight_rates WHERE origin = ? AND shipping_type = ?
            """, (origin, shipping_type))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result['rate'] if result else None
        except Exception as e:
            print(f"Error al obtener tarifa de flete: {e}")
            return None
    
    @staticmethod
    def set_freight_rate(origin: str, shipping_type: str, rate: float, unit: str, updated_by: int = None) -> bool:
        """Establece una tarifa de flete."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            
            # Verificar si ya existe
            cursor.execute("""
                SELECT COUNT(*) FROM freight_rates WHERE origin = %s AND shipping_type = %s
            """ if is_postgres else """
                SELECT COUNT(*) FROM freight_rates WHERE origin = ? AND shipping_type = ?
            """, (origin, shipping_type))
            
            result = cursor.fetchone()
            exists = result[0] if is_postgres else result[0]
            
            if exists > 0:
                # Actualizar
                cursor.execute("""
                    UPDATE freight_rates SET rate = %s, unit = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE origin = %s AND shipping_type = %s
                """ if is_postgres else """
                    UPDATE freight_rates SET rate = ?, unit = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE origin = ? AND shipping_type = ?
                """, (rate, unit, updated_by, origin, shipping_type))
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO freight_rates (origin, shipping_type, rate, unit, updated_by)
                    VALUES (%s, %s, %s, %s, %s)
                """ if is_postgres else """
                    INSERT INTO freight_rates (origin, shipping_type, rate, unit, updated_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (origin, shipping_type, rate, unit, updated_by))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al establecer tarifa de flete: {e}")
            return False
    
    @staticmethod
    def get_all_freight_rates() -> List[Dict[str, Any]]:
        """Obtiene todas las tarifas de flete."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM freight_rates")
            rates = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return rates
        except Exception as e:
            print(f"Error al obtener tarifas de flete: {e}")
            return []
    
    # ==================== MÉTODOS DE LOGS ====================
    
    @staticmethod
    def log_activity(user_id: int, action: str, details: str = "") -> bool:
        """Registra una actividad en el log."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                INSERT INTO activity_logs (user_id, action, details)
                VALUES (%s, %s, %s)
            """ if is_postgres else """
                INSERT INTO activity_logs (user_id, action, details)
                VALUES (?, ?, ?)
            """, (user_id, action, details))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al registrar actividad: {e}")
            return False
