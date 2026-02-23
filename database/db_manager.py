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
    
    # Detectar DATABASE_URL con logging mejorado
    # Buscar en múltiples variables de entorno posibles
    _database_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("POSTGRES_URL") or 
        os.getenv("POSTGRESQL_URL") or
        os.getenv("DB_URL")
    )
    
    # Detección simple y segura
    USE_POSTGRES = _database_url is not None
    
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
                email TEXT,
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
        
        # Tabla 8: password_reset_tokens (tokens de recuperación de contraseña)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id {id_type},
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tabla 9: freight_rates (tarifas de flete)
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
        
        # Tabla 10: quote_history (historial de cambios de cotizaciones)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS quote_history (
                id {id_type},
                quote_id INTEGER NOT NULL,
                edited_by INTEGER NOT NULL,
                edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                field_changed TEXT,
                old_value TEXT,
                new_value TEXT,
                change_summary TEXT,
                FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
                FOREIGN KEY (edited_by) REFERENCES users(id)
            )
        """)
        
        # Tabla 11: quote_notifications (notificaciones de cotizaciones)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS quote_notifications (
                id {id_type},
                quote_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL CHECK(notification_type IN ('status_change', 'edit', 'comment')),
                message TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_by_user INTEGER DEFAULT 0,
                read_at TIMESTAMP,
                FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        
        # ==================== MIGRACIONES AUTOMÁTICAS ====================
        # Migración: Agregar columna 'email' a tabla 'users' si no existe
        try:
            if is_postgres:
                # PostgreSQL: Verificar si la columna existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='email'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
                    conn.commit()
                    print("✅ Migración: Columna 'email' agregada a tabla 'users'")
            else:
                # SQLite: Verificar si la columna existe
                cursor.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'email' not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
                    conn.commit()
                    print("✅ Migración: Columna 'email' agregada a tabla 'users'")
        except Exception as e:
            print(f"⚠️ Migración de columna 'email': {e}")
        
        # Migración: Agregar columnas adicionales a tabla 'quotes'
        try:
            if is_postgres:
                # Verificar y agregar columnas faltantes en quotes
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='quotes' AND column_name IN ('client_cedula', 'client_address', 'client_vehicle', 'client_year', 'client_vin', 'sub_total', 'iva_total', 'abona_ya', 'en_entrega', 'terms_conditions')
                """)
                existing_cols = [row['column_name'] for row in cursor.fetchall()]
                
                if 'client_cedula' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_cedula TEXT")
                if 'client_address' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_address TEXT")
                if 'client_vehicle' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_vehicle TEXT")
                if 'client_year' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_year TEXT")
                if 'client_vin' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_vin TEXT")
                if 'sub_total' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN sub_total REAL DEFAULT 0")
                if 'iva_total' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN iva_total REAL DEFAULT 0")
                if 'abona_ya' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN abona_ya REAL DEFAULT 0")
                if 'en_entrega' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN en_entrega REAL DEFAULT 0")
                if 'terms_conditions' not in existing_cols:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN terms_conditions TEXT")
                
                conn.commit()
                print("✅ Migración: Columnas adicionales agregadas a tabla 'quotes'")
            else:
                # SQLite
                cursor.execute("PRAGMA table_info(quotes)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'client_cedula' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_cedula TEXT")
                if 'client_address' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_address TEXT")
                if 'client_vehicle' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_vehicle TEXT")
                if 'client_year' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_year TEXT")
                if 'client_vin' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN client_vin TEXT")
                if 'sub_total' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN sub_total REAL DEFAULT 0")
                if 'iva_total' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN iva_total REAL DEFAULT 0")
                if 'abona_ya' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN abona_ya REAL DEFAULT 0")
                if 'en_entrega' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN en_entrega REAL DEFAULT 0")
                if 'terms_conditions' not in columns:
                    cursor.execute("ALTER TABLE quotes ADD COLUMN terms_conditions TEXT")
                
                conn.commit()
                print("✅ Migración: Columnas adicionales agregadas a tabla 'quotes'")
        except Exception as e:
            print(f"⚠️ Migración de columnas en 'quotes': {e}")
        
        # Migración: Agregar columnas adicionales a tabla 'quote_items'
        try:
            if is_postgres:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='quote_items' AND column_name IN ('marca', 'garantia', 'total_cost', 'envio_tipo', 'origen', 'fabricacion', 'tiempo_entrega')
                """)
                existing_cols = [row['column_name'] for row in cursor.fetchall()]
                
                if 'marca' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN marca TEXT")
                if 'garantia' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN garantia TEXT")
                if 'total_cost' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN total_cost REAL DEFAULT 0")
                if 'envio_tipo' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN envio_tipo TEXT")
                if 'origen' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN origen TEXT")
                if 'fabricacion' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN fabricacion TEXT")
                if 'tiempo_entrega' not in existing_cols:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN tiempo_entrega TEXT")
                
                conn.commit()
                print("✅ Migración: Columnas adicionales agregadas a tabla 'quote_items'")
            else:
                cursor.execute("PRAGMA table_info(quote_items)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'marca' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN marca TEXT")
                if 'garantia' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN garantia TEXT")
                if 'total_cost' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN total_cost REAL DEFAULT 0")
                if 'envio_tipo' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN envio_tipo TEXT")
                if 'origen' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN origen TEXT")
                if 'fabricacion' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN fabricacion TEXT")
                if 'tiempo_entrega' not in columns:
                    cursor.execute("ALTER TABLE quote_items ADD COLUMN tiempo_entrega TEXT")
                
                conn.commit()
                print("✅ Migración: Columnas adicionales agregadas a tabla 'quote_items'")
        except Exception as e:
            print(f"⚠️ Migración de columnas en 'quote_items': {e}")
        
        # Crear usuario admin por defecto si no existe
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        # Para PostgreSQL con RealDictCursor, result es un dict; para SQLite es una tupla
        count = result['count'] if is_postgres else result[0]
        
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
    def create_user(username: str, password: str, full_name: str, role: str, email: str = None) -> bool:
        """Crea un nuevo usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, email, role)
                VALUES (%s, %s, %s, %s, %s)
            """ if is_postgres else """
                INSERT INTO users (username, password_hash, full_name, email, role)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash.decode('utf-8'), full_name, email, role))
            
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
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un usuario por su ID."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT * FROM users WHERE id = %s
            """ if is_postgres else """
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            print(f"Error al obtener usuario por ID: {e}")
            return None
    
    @staticmethod
    def update_user(user_id: int, full_name: str, role: str, email: str = None, username: str = None) -> bool:
        """Actualiza el nombre completo, rol, email y username de un usuario."""
        try:
            print(f"[DEBUG] update_user llamado con:")
            print(f"  - user_id: {user_id}")
            print(f"  - username: {username}")
            print(f"  - full_name: {full_name}")
            print(f"  - role: {role}")
            print(f"  - email: {email}")
            
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            print(f"[DEBUG] Usando {'PostgreSQL' if is_postgres else 'SQLite'}")
            
            # Si se proporciona username, actualizar también
            if username:
                cursor.execute("""
                    UPDATE users SET username = %s, full_name = %s, role = %s, email = %s WHERE id = %s
                """ if is_postgres else """
                    UPDATE users SET username = ?, full_name = ?, role = ?, email = ? WHERE id = ?
                """, (username, full_name, role, email, user_id))
            else:
                cursor.execute("""
                    UPDATE users SET full_name = %s, role = %s, email = %s WHERE id = %s
                """ if is_postgres else """
                    UPDATE users SET full_name = ?, role = ?, email = ? WHERE id = ?
                """, (full_name, role, email, user_id))
            
            rows_affected = cursor.rowcount
            print(f"[DEBUG] Filas actualizadas: {rows_affected}")
            
            conn.commit()
            
            # Verificar que se guardó correctamente
            cursor.execute("""
                SELECT email FROM users WHERE id = %s
            """ if is_postgres else """
                SELECT email FROM users WHERE id = ?
            """, (user_id,))
            result = cursor.fetchone()
            saved_email = result['email'] if (result and is_postgres) else (result[0] if result else None)
            print(f"[DEBUG] Email guardado en BD: {saved_email}")
            
            cursor.close()
            conn.close()
            
            if saved_email == email:
                print(f"[DEBUG] ✅ Email guardado correctamente")
                return True
            else:
                print(f"[DEBUG] ⚠️ Email guardado ({saved_email}) no coincide con el esperado ({email})")
                return True  # Retornar True de todas formas porque el UPDATE fue exitoso
        except Exception as e:
            print(f"[ERROR] Error al actualizar usuario: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def change_password(user_id: int, new_password: str) -> bool:
        """Cambia la contraseña de un usuario."""
        conn = None
        cursor = None
        try:
            import bcrypt
            
            # Hash de la nueva contraseña
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                UPDATE users SET password_hash = %s WHERE id = %s
            """ if is_postgres else """
                UPDATE users SET password_hash = ? WHERE id = ?
            """, (hashed_password.decode('utf-8'), user_id))
            
            # Verificar que se actualizó al menos una fila
            rows_affected = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if rows_affected == 0:
                print(f"⚠️ Advertencia: No se encontró usuario con ID {user_id}")
                return False
            
            print(f"✅ Contraseña actualizada exitosamente para usuario ID {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error al cambiar contraseña: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
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
            exists = result['count'] if is_postgres else result[0]
            
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
            print(f"Error al establecer configuración '{key}': {e}")
            import traceback
            traceback.print_exc()
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
            exists = result['count'] if is_postgres else result[0]
            
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

    # ==================== MÉTODOS ALIAS ====================
    
    @staticmethod
    def update_config(key: str, value: str, updated_by: int = None) -> bool:
        """Alias de set_config para compatibilidad."""
        return DBManager.set_config(key, value, "", updated_by)
    
    @staticmethod
    def update_freight_rate(origin: str, shipping_type: str, rate: float, updated_by: int = None) -> bool:
        """Actualiza una tarifa de flete."""
        # Determinar la unidad según origen y tipo
        if origin == "Miami" and shipping_type == "Aéreo":
            unit = "$/lb"
        elif origin == "Miami" and shipping_type == "Marítimo":
            unit = "$/ft³"
        elif origin == "Madrid" and shipping_type == "Aéreo":
            unit = "$/kg"
        else:
            unit = "$"
        
        return DBManager.set_freight_rate(origin, shipping_type, rate, unit, updated_by)
    
    # ==================== MÉTODOS DE REPORTES Y ESTADÍSTICAS ====================
    
    @staticmethod
    def get_quote_stats() -> Dict[str, Any]:
        """Obtiene estadísticas de cotizaciones."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            # Total de cotizaciones
            cursor.execute("SELECT COUNT(*) as total FROM quotes")
            result = cursor.fetchone()
            total = result['total'] if (result and is_postgres) else (result[0] if result else 0)
            
            # Por estado
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM quotes 
                GROUP BY status
            """)
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Por analista
            cursor.execute("""
                SELECT u.full_name, COUNT(q.id) as count
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                GROUP BY u.full_name
            """)
            by_analyst = {row['full_name']: row['count'] for row in cursor.fetchall()}
            
            cursor.close()
            conn.close()
            
            return {
                'total': total,
                'by_status': by_status,
                'by_analyst': by_analyst
            }
        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
            return {
                'total': 0,
                'by_status': {},
                'by_analyst': {}
            }
    
    @staticmethod
    def get_quotes_by_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Obtiene cotizaciones por período."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT q.*, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE DATE(q.created_at) >= %s AND DATE(q.created_at) <= %s
                ORDER BY q.created_at DESC
            """ if is_postgres else """
                SELECT q.*, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE DATE(q.created_at) >= ? AND DATE(q.created_at) <= ?
                ORDER BY q.created_at DESC
            """, (start_date, end_date))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return quotes
        except Exception as e:
            print(f"Error al obtener cotizaciones por período: {e}")
            return []
    
    @staticmethod
    def get_recent_activities(limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene las actividades recientes del sistema."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            is_postgres = DBManager.USE_POSTGRES
            cursor.execute("""
                SELECT a.*, u.full_name
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT %s
            """ if is_postgres else """
                SELECT a.*, u.full_name
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT ?
            """, (limit,))
            
            activities = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return activities
        except Exception as e:
            print(f"Error al obtener actividades recientes: {e}")
            return []

    # ==================== MÉTODOS DE RECUPERACIÓN DE CONTRASEÑA ====================
    
    @staticmethod
    def create_reset_token(user_id: int, token: str, expires_at: datetime) -> bool:
        """Crea un token de recuperación de contraseña."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            if DBManager.USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (%s, %s, %s)
                """, (user_id, token, expires_at))
            else:
                cursor.execute("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                """, (user_id, token, expires_at))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al crear token de reset: {e}")
            return False
    
    @staticmethod
    def get_reset_token(token: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un token de reset."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            if DBManager.USE_POSTGRES:
                cursor.execute("""
                    SELECT * FROM password_reset_tokens
                    WHERE token = %s AND used = 0
                """, (token,))
            else:
                cursor.execute("""
                    SELECT * FROM password_reset_tokens
                    WHERE token = ? AND used = 0
                """, (token,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return dict(result) if DBManager.USE_POSTGRES else dict(zip([col[0] for col in cursor.description], result))
            return None
        except Exception as e:
            print(f"Error al obtener token de reset: {e}")
            return None
    
    @staticmethod
    def get_recent_reset_token(user_id: int, minutes: int = 5) -> Optional[Dict[str, Any]]:
        """Obtiene el token más reciente de un usuario si fue creado en los últimos N minutos."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            if DBManager.USE_POSTGRES:
                cursor.execute("""
                    SELECT * FROM password_reset_tokens
                    WHERE user_id = %s 
                    AND created_at > NOW() - INTERVAL '%s minutes'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id, minutes))
            else:
                cursor.execute("""
                    SELECT * FROM password_reset_tokens
                    WHERE user_id = ? 
                    AND datetime(created_at) > datetime('now', '-' || ? || ' minutes')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id, minutes))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return dict(result) if DBManager.USE_POSTGRES else dict(zip([col[0] for col in cursor.description], result))
            return None
        except Exception as e:
            print(f"Error al obtener token reciente: {e}")
            return None
    
    @staticmethod
    def mark_token_as_used(token: str) -> bool:
        """Marca un token como usado."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            if DBManager.USE_POSTGRES:
                cursor.execute("""
                    UPDATE password_reset_tokens
                    SET used = 1
                    WHERE token = %s
                """, (token,))
            else:
                cursor.execute("""
                    UPDATE password_reset_tokens
                    SET used = 1
                    WHERE token = ?
                """, (token,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al marcar token como usado: {e}")
            return False
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Obtiene un usuario por su email."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            if DBManager.USE_POSTGRES:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            else:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return dict(result) if DBManager.USE_POSTGRES else dict(zip([col[0] for col in cursor.description], result))
            return None
        except Exception as e:
            print(f"Error al obtener usuario por email: {e}")
            return None
    
    # ==================== MÉTODOS HELPER PARA TOKENS (COMPATIBILIDAD) ====================
    
    @staticmethod
    def create_password_reset_token(user_id: int) -> Optional[str]:
        """Crea un token de recuperación y lo retorna (método helper)."""
        try:
            import secrets
            from datetime import timedelta
            
            # Generar token único
            token = secrets.token_urlsafe(32)
            
            # Calcular fecha de expiración (1 hora)
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Guardar en base de datos
            if DBManager.create_reset_token(user_id, token, expires_at):
                return token
            return None
        except Exception as e:
            print(f"Error al crear token de reset: {e}")
            return None
    
    @staticmethod
    def verify_reset_token(token: str) -> Optional[int]:
        """Verifica un token y retorna el user_id si es válido."""
        try:
            token_data = DBManager.get_reset_token(token)
            
            if not token_data:
                return None
            
            # Verificar si expiró
            expires_at = datetime.fromisoformat(str(token_data['expires_at']))
            if datetime.now() > expires_at:
                return None
            
            return token_data['user_id']
        except Exception as e:
            print(f"Error al verificar token: {e}")
            return None
    
    @staticmethod
    def use_reset_token(token: str) -> bool:
        """Marca un token como usado (alias de mark_token_as_used)."""
        return DBManager.mark_token_as_used(token)


    # ==================== MÉTODOS DE GESTIÓN DE COTIZACIONES ====================
    
    @staticmethod
    def save_quote(quote_data: Dict[str, Any]) -> Optional[int]:
        """
        Guarda una cotización completa en la base de datos.
        
        Args:
            quote_data: Diccionario con los datos de la cotización:
                - quote_number: Número de cotización (ej: 2026-30022-A)
                - analyst_id: ID del analista
                - client_name: Nombre del cliente
                - client_phone: Teléfono del cliente
                - client_email: Email del cliente
                - client_cedula: Cédula o RIF del cliente
                - client_address: Dirección del cliente
                - client_vehicle: Vehículo del cliente
                - client_year: Año del vehículo
                - client_vin: VIN del vehículo
                - total_amount: Monto total
                - sub_total: Subtotal
                - iva_total: IVA total
                - abona_ya: Monto de abono
                - en_entrega: Monto en entrega
                - terms_conditions: Términos y condiciones
                - status: Estado (draft/sent/approved/rejected)
                - pdf_path: Ruta del archivo PDF
                - jpeg_path: Ruta del archivo PNG/JPEG
        
        Returns:
            ID de la cotización guardada o None si hay error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Preparar datos con valores por defecto
            quote_number = quote_data.get('quote_number')
            analyst_id = quote_data.get('analyst_id')
            client_name = quote_data.get('client_name', '')
            client_phone = quote_data.get('client_phone', '')
            client_email = quote_data.get('client_email', '')
            client_cedula = quote_data.get('client_cedula', '')
            client_address = quote_data.get('client_address', '')
            client_vehicle = quote_data.get('client_vehicle', '')
            client_year = quote_data.get('client_year', '')
            client_vin = quote_data.get('client_vin', '')
            total_amount = quote_data.get('total_amount', 0.0)
            sub_total = quote_data.get('sub_total', 0.0)
            iva_total = quote_data.get('iva_total', 0.0)
            abona_ya = quote_data.get('abona_ya', 0.0)
            en_entrega = quote_data.get('en_entrega', 0.0)
            terms_conditions = quote_data.get('terms_conditions', '')
            status = quote_data.get('status', 'draft')
            pdf_path = quote_data.get('pdf_path', '')
            jpeg_path = quote_data.get('jpeg_path', '')
            
            # Validar campos obligatorios
            if not quote_number or not analyst_id:
                print("Error: quote_number y analyst_id son obligatorios")
                return None
            
            # Insertar cotización
            if is_postgres:
                cursor.execute("""
                    INSERT INTO quotes (
                        quote_number, analyst_id, client_name, client_phone, client_email,
                        client_cedula, client_address, client_vehicle, client_year, client_vin,
                        total_amount, sub_total, iva_total, abona_ya, en_entrega,
                        terms_conditions, status, pdf_path, jpeg_path
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    quote_number, analyst_id, client_name, client_phone, client_email,
                    client_cedula, client_address, client_vehicle, client_year, client_vin,
                    total_amount, sub_total, iva_total, abona_ya, en_entrega,
                    terms_conditions, status, pdf_path, jpeg_path
                ))
                quote_id = cursor.fetchone()['id']
            else:
                cursor.execute("""
                    INSERT INTO quotes (
                        quote_number, analyst_id, client_name, client_phone, client_email,
                        client_cedula, client_address, client_vehicle, client_year, client_vin,
                        total_amount, sub_total, iva_total, abona_ya, en_entrega,
                        terms_conditions, status, pdf_path, jpeg_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    quote_number, analyst_id, client_name, client_phone, client_email,
                    client_cedula, client_address, client_vehicle, client_year, client_vin,
                    total_amount, sub_total, iva_total, abona_ya, en_entrega,
                    terms_conditions, status, pdf_path, jpeg_path
                ))
                quote_id = cursor.lastrowid
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Cotización guardada exitosamente: {quote_number} (ID: {quote_id})")
            return quote_id
            
        except Exception as e:
            print(f"❌ Error al guardar cotización: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def save_quote_items(quote_id: int, items: List[Dict[str, Any]]) -> bool:
        """
        Guarda los ítems de una cotización.
        
        Args:
            quote_id: ID de la cotización
            items: Lista de diccionarios con los datos de cada ítem:
                - description: Descripción del repuesto
                - part_number: Número de parte
                - marca: Marca
                - garantia: Garantía
                - quantity: Cantidad
                - unit_cost: Costo unitario
                - total_cost: Costo total
                - envio_tipo: Tipo de envío
                - origen: Origen
                - fabricacion: Fabricación
                - tiempo_entrega: Tiempo de entrega
                - page_url: URL de la página donde se cotizó
        
        Returns:
            True si se guardaron exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            for item in items:
                description = item.get('descripcion', '') or item.get('description', '')
                part_number = item.get('parte', '') or item.get('part_number', '')
                marca = item.get('marca', '')
                garantia = item.get('garantia', '')
                quantity = item.get('cantidad', 1) or item.get('quantity', 1)
                unit_cost = item.get('precio_unitario', 0.0) or item.get('unit_cost', 0.0)
                total_cost = item.get('precio_bs', 0.0) or item.get('total_cost', 0.0)
                envio_tipo = item.get('envio_tipo', '')
                origen = item.get('origen', '')
                fabricacion = item.get('fabricacion', '')
                tiempo_entrega = item.get('tiempo_entrega', '')
                page_url = item.get('page_url', '') or item.get('link', '')
                
                # Calcular unit_cost si no está presente
                if unit_cost == 0.0 and total_cost > 0 and quantity > 0:
                    unit_cost = total_cost / quantity
                
                # Obtener costos internos
                costo_fob = item.get('costo_fob', 0.0)
                costo_handling = item.get('costo_handling', 0.0)
                costo_manejo = item.get('costo_manejo', 0.0)
                costo_envio = item.get('costo_envio', 0.0)
                impuesto_porcentaje = item.get('impuesto_porcentaje', 0.0)
                factor_utilidad = item.get('factor_utilidad', 1.0)
                
                if is_postgres:
                    cursor.execute("""
                        INSERT INTO quote_items (
                            quote_id, description, part_number, marca, garantia,
                            quantity, unit_cost, total_cost, envio_tipo, origen,
                            fabricacion, tiempo_entrega, page_url,
                            international_handling, national_handling, shipping_cost,
                            tax_percentage, profit_factor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        quote_id, description, part_number, marca, garantia,
                        quantity, unit_cost, total_cost, envio_tipo, origen,
                        fabricacion, tiempo_entrega, page_url,
                        costo_handling, costo_manejo, costo_envio,
                        impuesto_porcentaje, factor_utilidad
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO quote_items (
                            quote_id, description, part_number, marca, garantia,
                            quantity, unit_cost, total_cost, envio_tipo, origen,
                            fabricacion, tiempo_entrega, page_url,
                            international_handling, national_handling, shipping_cost,
                            tax_percentage, profit_factor
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        quote_id, description, part_number, marca, garantia,
                        quantity, unit_cost, total_cost, envio_tipo, origen,
                        fabricacion, tiempo_entrega, page_url,
                        costo_handling, costo_manejo, costo_envio,
                        impuesto_porcentaje, factor_utilidad
                    ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ {len(items)} ítems guardados para cotización ID: {quote_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error al guardar ítems de cotización: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_quotes_by_analyst(analyst_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene todas las cotizaciones de un analista específico.
        
        Args:
            analyst_id: ID del analista
            limit: Número máximo de cotizaciones a retornar
        
        Returns:
            Lista de diccionarios con las cotizaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if is_postgres:
                cursor.execute("""
                    SELECT * FROM quotes
                    WHERE analyst_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (analyst_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM quotes
                    WHERE analyst_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (analyst_id, limit))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return quotes
            
        except Exception as e:
            print(f"❌ Error al obtener cotizaciones del analista: {e}")
            return []
    
    @staticmethod
    def get_all_quotes(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene todas las cotizaciones del sistema (para administrador).
        
        Args:
            limit: Número máximo de cotizaciones a retornar
        
        Returns:
            Lista de diccionarios con las cotizaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if is_postgres:
                cursor.execute("""
                    SELECT q.*, u.full_name as analyst_name
                    FROM quotes q
                    JOIN users u ON q.analyst_id = u.id
                    ORDER BY q.created_at DESC
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT q.*, u.full_name as analyst_name
                    FROM quotes q
                    JOIN users u ON q.analyst_id = u.id
                    ORDER BY q.created_at DESC
                    LIMIT ?
                """, (limit,))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return quotes
            
        except Exception as e:
            print(f"❌ Error al obtener todas las cotizaciones: {e}")
            return []
    
    @staticmethod
    def get_quote_by_id(quote_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una cotización específica por su ID.
        
        Args:
            quote_id: ID de la cotización
        
        Returns:
            Diccionario con los datos de la cotización o None si no existe
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if is_postgres:
                cursor.execute("""
                    SELECT q.*, u.full_name as analyst_name
                    FROM quotes q
                    JOIN users u ON q.analyst_id = u.id
                    WHERE q.id = %s
                """, (quote_id,))
            else:
                cursor.execute("""
                    SELECT q.*, u.full_name as analyst_name
                    FROM quotes q
                    JOIN users u ON q.analyst_id = u.id
                    WHERE q.id = ?
                """, (quote_id,))
            
            quote = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(quote) if quote else None
            
        except Exception as e:
            print(f"❌ Error al obtener cotización por ID: {e}")
            return None
    
    @staticmethod
    def get_quote_items(quote_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los ítems de una cotización.
        
        Args:
            quote_id: ID de la cotización
        
        Returns:
            Lista de diccionarios con los ítems
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if is_postgres:
                cursor.execute("""
                    SELECT * FROM quote_items
                    WHERE quote_id = %s
                    ORDER BY id
                """, (quote_id,))
            else:
                cursor.execute("""
                    SELECT * FROM quote_items
                    WHERE quote_id = ?
                    ORDER BY id
                """, (quote_id,))
            
            items = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return items
            
        except Exception as e:
            print(f"❌ Error al obtener ítems de cotización: {e}")
            return []
    
    @staticmethod
    def search_quotes(analyst_id: Optional[int], search_term: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca cotizaciones por número, nombre de cliente o teléfono.
        
        Args:
            analyst_id: ID del analista (None para buscar en todas)
            search_term: Término de búsqueda
            limit: Número máximo de resultados
        
        Returns:
            Lista de diccionarios con las cotizaciones encontradas
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            search_pattern = f"%{search_term}%"
            
            if analyst_id:
                # Buscar solo cotizaciones del analista
                if is_postgres:
                    cursor.execute("""
                        SELECT * FROM quotes
                        WHERE analyst_id = %s
                        AND (quote_number ILIKE %s OR client_name ILIKE %s OR client_phone ILIKE %s)
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (analyst_id, search_pattern, search_pattern, search_pattern, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM quotes
                        WHERE analyst_id = ?
                        AND (quote_number LIKE ? OR client_name LIKE ? OR client_phone LIKE ?)
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (analyst_id, search_pattern, search_pattern, search_pattern, limit))
            else:
                # Buscar en todas las cotizaciones (administrador)
                if is_postgres:
                    cursor.execute("""
                        SELECT q.*, u.full_name as analyst_name
                        FROM quotes q
                        JOIN users u ON q.analyst_id = u.id
                        WHERE quote_number ILIKE %s OR client_name ILIKE %s OR client_phone ILIKE %s
                        ORDER BY q.created_at DESC
                        LIMIT %s
                    """, (search_pattern, search_pattern, search_pattern, limit))
                else:
                    cursor.execute("""
                        SELECT q.*, u.full_name as analyst_name
                        FROM quotes q
                        JOIN users u ON q.analyst_id = u.id
                        WHERE quote_number LIKE ? OR client_name LIKE ? OR client_phone LIKE ?
                        ORDER BY q.created_at DESC
                        LIMIT ?
                    """, (search_pattern, search_pattern, search_pattern, limit))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return quotes
            
        except Exception as e:
            print(f"❌ Error al buscar cotizaciones: {e}")
            return []

    # ==================== FUNCIONES DE EDICIÓN DE COTIZACIONES ====================
    
    @staticmethod
    def get_quote_full_details(quote_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los detalles de una cotización incluyendo ítems e historial.
        
        Args:
            quote_id: ID de la cotización
            
        Returns:
            Diccionario con todos los datos de la cotización o None si no existe
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Obtener datos de la cotización
            cursor.execute("""
                SELECT q.*, u.full_name as analyst_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.id = %s
            """ if is_postgres else """
                SELECT q.*, u.full_name as analyst_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.id = ?
            """, (quote_id,))
            
            quote = cursor.fetchone()
            if not quote:
                cursor.close()
                conn.close()
                return None
            
            quote_data = dict(quote)
            
            # Obtener ítems de la cotización
            cursor.execute("""
                SELECT * FROM quote_items WHERE quote_id = %s ORDER BY id
            """ if is_postgres else """
                SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id
            """, (quote_id,))
            
            items = [dict(row) for row in cursor.fetchall()]
            quote_data['items'] = items
            
            # Obtener historial de cambios
            cursor.execute("""
                SELECT qh.*, u.full_name as editor_name
                FROM quote_history qh
                JOIN users u ON qh.edited_by = u.id
                WHERE qh.quote_id = %s
                ORDER BY qh.edited_at DESC
                LIMIT 50
            """ if is_postgres else """
                SELECT qh.*, u.full_name as editor_name
                FROM quote_history qh
                JOIN users u ON qh.edited_by = u.id
                WHERE qh.quote_id = ?
                ORDER BY qh.edited_at DESC
                LIMIT 50
            """, (quote_id,))
            
            history = [dict(row) for row in cursor.fetchall()]
            quote_data['history'] = history
            
            cursor.close()
            conn.close()
            
            return quote_data
            
        except Exception as e:
            print(f"❌ Error al obtener detalles completos de cotización: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def update_quote(quote_id: int, quote_data: Dict[str, Any], edited_by: int) -> bool:
        """
        Actualiza los datos principales de una cotización y registra el cambio en el historial.
        
        Args:
            quote_id: ID de la cotización a actualizar
            quote_data: Diccionario con los nuevos datos
            edited_by: ID del usuario que realiza la edición
            
        Returns:
            True si se actualizó exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Obtener datos antiguos para el historial
            cursor.execute("""
                SELECT * FROM quotes WHERE id = %s
            """ if is_postgres else """
                SELECT * FROM quotes WHERE id = ?
            """, (quote_id,))
            
            old_quote = dict(cursor.fetchone())
            
            # Actualizar cotización
            cursor.execute("""
                UPDATE quotes SET
                    client_name = %s,
                    client_phone = %s,
                    client_email = %s,
                    client_cedula = %s,
                    client_address = %s,
                    client_vehicle = %s,
                    client_year = %s,
                    client_vin = %s,
                    total_amount = %s,
                    sub_total = %s,
                    iva_total = %s,
                    abona_ya = %s,
                    en_entrega = %s,
                    terms_conditions = %s,
                    pdf_path = %s,
                    jpeg_path = %s
                WHERE id = %s
            """ if is_postgres else """
                UPDATE quotes SET
                    client_name = ?,
                    client_phone = ?,
                    client_email = ?,
                    client_cedula = ?,
                    client_address = ?,
                    client_vehicle = ?,
                    client_year = ?,
                    client_vin = ?,
                    total_amount = ?,
                    sub_total = ?,
                    iva_total = ?,
                    abona_ya = ?,
                    en_entrega = ?,
                    terms_conditions = ?,
                    pdf_path = ?,
                    jpeg_path = ?
                WHERE id = ?
            """, (
                quote_data.get('client_name'),
                quote_data.get('client_phone'),
                quote_data.get('client_email'),
                quote_data.get('client_cedula'),
                quote_data.get('client_address'),
                quote_data.get('client_vehicle'),
                quote_data.get('client_year'),
                quote_data.get('client_vin'),
                quote_data.get('total_amount'),
                quote_data.get('sub_total'),
                quote_data.get('iva_total'),
                quote_data.get('abona_ya'),
                quote_data.get('en_entrega'),
                quote_data.get('terms_conditions'),
                quote_data.get('pdf_path'),
                quote_data.get('jpeg_path'),
                quote_id
            ))
            
            # Registrar cambios en el historial
            changes = []
            if old_quote['client_name'] != quote_data.get('client_name'):
                changes.append(f"Nombre: {old_quote['client_name']} → {quote_data.get('client_name')}")
            if old_quote['client_phone'] != quote_data.get('client_phone'):
                changes.append(f"Teléfono: {old_quote['client_phone']} → {quote_data.get('client_phone')}")
            if old_quote['total_amount'] != quote_data.get('total_amount'):
                changes.append(f"Total: ${old_quote['total_amount']:.2f} → ${quote_data.get('total_amount'):.2f}")
            
            if changes:
                change_summary = "Editó datos de la cotización: " + ", ".join(changes)
                DBManager.log_quote_change(
                    quote_id,
                    edited_by,
                    'quote_data',
                    str(old_quote),
                    str(quote_data),
                    change_summary
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Cotización {quote_id} actualizada exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar cotización: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def update_quote_items(quote_id: int, items: List[Dict[str, Any]], edited_by: int) -> bool:
        """
        Actualiza los ítems de una cotización (elimina los antiguos e inserta los nuevos).
        
        Args:
            quote_id: ID de la cotización
            items: Lista de diccionarios con los nuevos ítems
            edited_by: ID del usuario que realiza la edición
            
        Returns:
            True si se actualizaron exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Obtener ítems antiguos para el historial
            cursor.execute("""
                SELECT COUNT(*) as count FROM quote_items WHERE quote_id = %s
            """ if is_postgres else """
                SELECT COUNT(*) as count FROM quote_items WHERE quote_id = ?
            """, (quote_id,))
            
            old_count = cursor.fetchone()
            old_count = old_count['count'] if is_postgres else old_count[0]
            
            # Eliminar ítems antiguos
            cursor.execute("""
                DELETE FROM quote_items WHERE quote_id = %s
            """ if is_postgres else """
                DELETE FROM quote_items WHERE quote_id = ?
            """, (quote_id,))
            
            # Insertar nuevos ítems
            for item in items:
                # Obtener costos internos
                costo_fob = item.get('costo_fob', 0.0)
                costo_handling = item.get('costo_handling', 0.0)
                costo_manejo = item.get('costo_manejo', 0.0)
                costo_envio = item.get('costo_envio', 0.0)
                impuesto_porcentaje = item.get('impuesto_porcentaje', 0.0)
                factor_utilidad = item.get('factor_utilidad', 1.0)
                
                cursor.execute("""
                    INSERT INTO quote_items (
                        quote_id, description, part_number, marca, garantia,
                        quantity, unit_cost, total_cost, envio_tipo, origen,
                        fabricacion, tiempo_entrega, page_url,
                        international_handling, national_handling, shipping_cost,
                        tax_percentage, profit_factor
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """ if is_postgres else """
                    INSERT INTO quote_items (
                        quote_id, description, part_number, marca, garantia,
                        quantity, unit_cost, total_cost, envio_tipo, origen,
                        fabricacion, tiempo_entrega, page_url,
                        international_handling, national_handling, shipping_cost,
                        tax_percentage, profit_factor
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    quote_id,
                    item.get('descripcion') or item.get('description', ''),
                    item.get('parte') or item.get('part_number', ''),
                    item.get('marca', ''),
                    item.get('garantia', ''),
                    item.get('cantidad') or item.get('quantity', 1),
                    item.get('unit') or item.get('unit_cost', 0),
                    item.get('total') or item.get('total_cost', 0),
                    item.get('envio_tipo', ''),
                    item.get('origen', ''),
                    item.get('fabricacion', ''),
                    item.get('tiempo_entrega', ''),
                    item.get('link') or item.get('page_url', ''),
                    costo_handling,
                    costo_manejo,
                    costo_envio,
                    impuesto_porcentaje,
                    factor_utilidad
                ))
            
            # Registrar cambio en el historial
            change_summary = f"Modificó ítems de la cotización ({old_count} → {len(items)} ítems)"
            DBManager.log_quote_change(
                quote_id,
                edited_by,
                'items',
                f"{old_count} ítems",
                f"{len(items)} ítems",
                change_summary
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Ítems de cotización {quote_id} actualizados exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar ítems de cotización: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def log_quote_change(quote_id: int, edited_by: int, field_changed: str, 
                        old_value: str, new_value: str, change_summary: str) -> bool:
        """
        Registra un cambio en el historial de una cotización.
        
        Args:
            quote_id: ID de la cotización
            edited_by: ID del usuario que realizó el cambio
            field_changed: Campo que cambió
            old_value: Valor anterior
            new_value: Valor nuevo
            change_summary: Resumen del cambio
            
        Returns:
            True si se registró exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                INSERT INTO quote_history (
                    quote_id, edited_by, field_changed, old_value, new_value, change_summary
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """ if is_postgres else """
                INSERT INTO quote_history (
                    quote_id, edited_by, field_changed, old_value, new_value, change_summary
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (quote_id, edited_by, field_changed, old_value, new_value, change_summary))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error al registrar cambio en historial: {e}")
            return False
    
    @staticmethod
    def get_quote_history(quote_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de cambios de una cotización.
        
        Args:
            quote_id: ID de la cotización
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de diccionarios con el historial de cambios
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT qh.*, u.full_name as editor_name
                FROM quote_history qh
                JOIN users u ON qh.edited_by = u.id
                WHERE qh.quote_id = %s
                ORDER BY qh.edited_at DESC
                LIMIT %s
            """ if is_postgres else """
                SELECT qh.*, u.full_name as editor_name
                FROM quote_history qh
                JOIN users u ON qh.edited_by = u.id
                WHERE qh.quote_id = ?
                ORDER BY qh.edited_at DESC
                LIMIT ?
            """, (quote_id, limit))
            
            history = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return history
            
        except Exception as e:
            print(f"❌ Error al obtener historial de cotización: {e}")
            return []
    
    # ==================== FUNCIONES DE CAMBIO DE ESTADO ====================
    
    @staticmethod
    def update_quote_status(quote_id: int, new_status: str, changed_by: int) -> bool:
        """
        Actualiza el estado de una cotización y registra el cambio.
        
        Args:
            quote_id: ID de la cotización
            new_status: Nuevo estado (draft/sent/approved/rejected)
            changed_by: ID del usuario que realiza el cambio
            
        Returns:
            True si se actualizó exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Obtener estado anterior
            cursor.execute("""
                SELECT status, quote_number FROM quotes WHERE id = %s
            """ if is_postgres else """
                SELECT status, quote_number FROM quotes WHERE id = ?
            """, (quote_id,))
            
            result = cursor.fetchone()
            old_status = result['status'] if is_postgres else result[0]
            quote_number = result['quote_number'] if is_postgres else result[1]
            
            # Actualizar estado
            cursor.execute("""
                UPDATE quotes SET status = %s WHERE id = %s
            """ if is_postgres else """
                UPDATE quotes SET status = ? WHERE id = ?
            """, (new_status, quote_id))
            
            # Mapeo de estados para mensajes
            status_names = {
                'draft': 'Borrador',
                'sent': 'Enviada',
                'approved': 'Aprobada',
                'rejected': 'Rechazada'
            }
            
            # Registrar cambio en historial
            change_summary = f"Cambió estado: {status_names.get(old_status, old_status)} → {status_names.get(new_status, new_status)}"
            DBManager.log_quote_change(
                quote_id,
                changed_by,
                'status',
                old_status,
                new_status,
                change_summary
            )
            
            # Crear notificación
            notification_message = f"Cotización #{quote_number} cambió de estado a '{status_names.get(new_status, new_status)}'"
            DBManager.create_notification(
                quote_id,
                'status_change',
                notification_message,
                changed_by
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Estado de cotización {quote_id} actualizado: {old_status} → {new_status}")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar estado de cotización: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== FUNCIONES DE NOTIFICACIONES ====================
    
    @staticmethod
    def create_notification(quote_id: int, notification_type: str, message: str, created_by: int) -> Optional[int]:
        """
        Crea una notificación para una cotización.
        
        Args:
            quote_id: ID de la cotización
            notification_type: Tipo de notificación (status_change/edit/comment)
            message: Mensaje de la notificación
            created_by: ID del usuario que crea la notificación
            
        Returns:
            ID de la notificación creada o None si hay error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                INSERT INTO quote_notifications (
                    quote_id, notification_type, message, created_by
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """ if is_postgres else """
                INSERT INTO quote_notifications (
                    quote_id, notification_type, message, created_by
                ) VALUES (?, ?, ?, ?)
            """, (quote_id, notification_type, message, created_by))
            
            if is_postgres:
                notification_id = cursor.fetchone()['id']
            else:
                notification_id = cursor.lastrowid
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return notification_id
            
        except Exception as e:
            print(f"❌ Error al crear notificación: {e}")
            return None
    
    @staticmethod
    def get_pending_notifications(user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene notificaciones pendientes.
        
        Args:
            user_id: ID del usuario (None para todas las notificaciones)
            limit: Número máximo de notificaciones a retornar
            
        Returns:
            Lista de diccionarios con las notificaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if user_id:
                # Notificaciones de cotizaciones del usuario
                cursor.execute("""
                    SELECT n.*, q.quote_number, u.full_name as creator_name
                    FROM quote_notifications n
                    JOIN quotes q ON n.quote_id = q.id
                    JOIN users u ON n.created_by = u.id
                    WHERE q.analyst_id = %s AND n.read_by_user = 0
                    ORDER BY n.created_at DESC
                    LIMIT %s
                """ if is_postgres else """
                    SELECT n.*, q.quote_number, u.full_name as creator_name
                    FROM quote_notifications n
                    JOIN quotes q ON n.quote_id = q.id
                    JOIN users u ON n.created_by = u.id
                    WHERE q.analyst_id = ? AND n.read_by_user = 0
                    ORDER BY n.created_at DESC
                    LIMIT ?
                """, (user_id, limit))
            else:
                # Todas las notificaciones (para admin)
                cursor.execute("""
                    SELECT n.*, q.quote_number, u.full_name as creator_name
                    FROM quote_notifications n
                    JOIN quotes q ON n.quote_id = q.id
                    JOIN users u ON n.created_by = u.id
                    WHERE n.read_by_user = 0
                    ORDER BY n.created_at DESC
                    LIMIT %s
                """ if is_postgres else """
                    SELECT n.*, q.quote_number, u.full_name as creator_name
                    FROM quote_notifications n
                    JOIN quotes q ON n.quote_id = q.id
                    JOIN users u ON n.created_by = u.id
                    WHERE n.read_by_user = 0
                    ORDER BY n.created_at DESC
                    LIMIT ?
                """, (limit,))
            
            notifications = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return notifications
            
        except Exception as e:
            print(f"❌ Error al obtener notificaciones: {e}")
            return []
    
    @staticmethod
    def mark_notification_as_read(notification_id: int) -> bool:
        """
        Marca una notificación como leída.
        
        Args:
            notification_id: ID de la notificación
            
        Returns:
            True si se marcó exitosamente, False en caso de error
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                UPDATE quote_notifications 
                SET read_by_user = 1, read_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """ if is_postgres else """
                UPDATE quote_notifications 
                SET read_by_user = 1, read_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (notification_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error al marcar notificación como leída: {e}")
            return False

    # ==================== FUNCIONES DE ESTADÍSTICAS ====================
    
    @staticmethod
    def get_analyst_statistics(analyst_id: int, period: str = 'all') -> Dict[str, Any]:
        """
        Calcula estadísticas del analista.
        
        Args:
            analyst_id: ID del analista
            period: 'month', 'quarter', 'year', 'all'
            
        Returns:
            Diccionario con estadísticas del analista
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Determinar filtro de fecha
            date_filter = ""
            if period == 'month':
                date_filter = "AND created_at >= CURRENT_DATE - INTERVAL '30 days'" if is_postgres else "AND created_at >= date('now', '-30 days')"
            elif period == 'quarter':
                date_filter = "AND created_at >= CURRENT_DATE - INTERVAL '90 days'" if is_postgres else "AND created_at >= date('now', '-90 days')"
            elif period == 'year':
                date_filter = "AND created_at >= CURRENT_DATE - INTERVAL '365 days'" if is_postgres else "AND created_at >= date('now', '-365 days')"
            
            # Total de cotizaciones
            cursor.execute(f"""
                SELECT COUNT(*) as total FROM quotes 
                WHERE analyst_id = {'%s' if is_postgres else '?'} {date_filter}
            """, (analyst_id,))
            total_quotes = cursor.fetchone()
            total_quotes = total_quotes['total'] if is_postgres else total_quotes[0]
            
            # Monto total cotizado
            cursor.execute(f"""
                SELECT COALESCE(SUM(total_amount), 0) as total FROM quotes 
                WHERE analyst_id = {'%s' if is_postgres else '?'} {date_filter}
            """, (analyst_id,))
            total_amount = cursor.fetchone()
            total_amount = total_amount['total'] if is_postgres else total_amount[0]
            
            # Distribución por estado
            cursor.execute(f"""
                SELECT status, COUNT(*) as count FROM quotes 
                WHERE analyst_id = {'%s' if is_postgres else '?'} {date_filter}
                GROUP BY status
            """, (analyst_id,))
            quotes_by_status = {}
            for row in cursor.fetchall():
                status = row['status'] if is_postgres else row[0]
                count = row['count'] if is_postgres else row[1]
                quotes_by_status[status] = count
            
            # Calcular tasa de aprobación
            approved = quotes_by_status.get('approved', 0)
            sent = quotes_by_status.get('sent', 0)
            rejected = quotes_by_status.get('rejected', 0)
            total_evaluated = approved + rejected + sent
            approval_rate = (approved / total_evaluated * 100) if total_evaluated > 0 else 0
            
            cursor.close()
            conn.close()
            
            return {
                'total_quotes': total_quotes,
                'total_amount': float(total_amount),
                'approval_rate': round(approval_rate, 2),
                'quotes_by_status': quotes_by_status
            }
            
        except Exception as e:
            print(f"❌ Error al obtener estadísticas del analista: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_quotes': 0,
                'total_amount': 0.0,
                'approval_rate': 0.0,
                'quotes_by_status': {}
            }
    
    @staticmethod
    def get_analyst_monthly_evolution(analyst_id: int, months: int = 6) -> List[Dict[str, Any]]:
        """
        Obtiene evolución mensual de cotizaciones del analista.
        
        Args:
            analyst_id: ID del analista
            months: Número de meses hacia atrás
            
        Returns:
            Lista de diccionarios con evolución mensual
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            if is_postgres:
                cursor.execute("""
                    SELECT 
                        TO_CHAR(created_at, 'Mon YYYY') as month,
                        COUNT(*) as quote_count,
                        COALESCE(SUM(total_amount), 0) as total_amount
                    FROM quotes
                    WHERE analyst_id = %s 
                    AND created_at >= CURRENT_DATE - INTERVAL '%s months'
                    GROUP BY TO_CHAR(created_at, 'Mon YYYY'), DATE_TRUNC('month', created_at)
                    ORDER BY DATE_TRUNC('month', created_at)
                """, (analyst_id, months))
            else:
                cursor.execute("""
                    SELECT 
                        strftime('%m/%Y', created_at) as month,
                        COUNT(*) as quote_count,
                        COALESCE(SUM(total_amount), 0) as total_amount
                    FROM quotes
                    WHERE analyst_id = ? 
                    AND created_at >= date('now', '-' || ? || ' months')
                    GROUP BY strftime('%m/%Y', created_at)
                    ORDER BY created_at
                """, (analyst_id, months))
            
            evolution = []
            for row in cursor.fetchall():
                evolution.append({
                    'month': row['month'] if is_postgres else row[0],
                    'quote_count': row['quote_count'] if is_postgres else row[1],
                    'total_amount': float(row['total_amount'] if is_postgres else row[2])
                })
            
            cursor.close()
            conn.close()
            
            return evolution
            
        except Exception as e:
            print(f"❌ Error al obtener evolución mensual: {e}")
            return []
    
    @staticmethod
    def get_global_statistics(period: str = 'all') -> Dict[str, Any]:
        """
        Calcula estadísticas globales de todos los analistas.
        
        Args:
            period: 'month', 'quarter', 'year', 'all'
            
        Returns:
            Diccionario con estadísticas globales
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Determinar filtro de fecha
            date_filter = ""
            if period == 'month':
                date_filter = "WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'" if is_postgres else "WHERE created_at >= date('now', '-30 days')"
            elif period == 'quarter':
                date_filter = "WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'" if is_postgres else "WHERE created_at >= date('now', '-90 days')"
            elif period == 'year':
                date_filter = "WHERE created_at >= CURRENT_DATE - INTERVAL '365 days'" if is_postgres else "WHERE created_at >= date('now', '-365 days')"
            
            # Total de cotizaciones
            cursor.execute(f"SELECT COUNT(*) as total FROM quotes {date_filter}")
            total_quotes = cursor.fetchone()
            total_quotes = total_quotes['total'] if is_postgres else total_quotes[0]
            
            # Monto total cotizado
            cursor.execute(f"SELECT COALESCE(SUM(total_amount), 0) as total FROM quotes {date_filter}")
            total_amount = cursor.fetchone()
            total_amount = total_amount['total'] if is_postgres else total_amount[0]
            
            # Distribución por estado
            cursor.execute(f"SELECT status, COUNT(*) as count FROM quotes {date_filter} GROUP BY status")
            quotes_by_status = {}
            for row in cursor.fetchall():
                status = row['status'] if is_postgres else row[0]
                count = row['count'] if is_postgres else row[1]
                quotes_by_status[status] = count
            
            # Calcular tasa de aprobación
            approved = quotes_by_status.get('approved', 0)
            sent = quotes_by_status.get('sent', 0)
            rejected = quotes_by_status.get('rejected', 0)
            total_evaluated = approved + rejected + sent
            approval_rate = (approved / total_evaluated * 100) if total_evaluated > 0 else 0
            
            # Contar analistas activos (con al menos una cotización)
            cursor.execute(f"SELECT COUNT(DISTINCT analyst_id) as count FROM quotes {date_filter}")
            active_analysts = cursor.fetchone()
            active_analysts = active_analysts['count'] if is_postgres else active_analysts[0]
            
            cursor.close()
            conn.close()
            
            return {
                'total_quotes': total_quotes,
                'total_amount': float(total_amount),
                'approval_rate': round(approval_rate, 2),
                'quotes_by_status': quotes_by_status,
                'active_analysts': active_analysts
            }
            
        except Exception as e:
            print(f"❌ Error al obtener estadísticas globales: {e}")
            return {
                'total_quotes': 0,
                'total_amount': 0.0,
                'approval_rate': 0.0,
                'quotes_by_status': {},
                'active_analysts': 0
            }
    
    @staticmethod
    def get_analyst_ranking(metric: str = 'quote_count', period: str = 'all', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene ranking de analistas.
        
        Args:
            metric: 'quote_count', 'total_amount', 'approval_rate'
            period: 'month', 'quarter', 'year', 'all'
            limit: Número máximo de analistas a retornar
            
        Returns:
            Lista ordenada de diccionarios con ranking
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Determinar filtro de fecha
            date_filter = ""
            if period == 'month':
                date_filter = "AND q.created_at >= CURRENT_DATE - INTERVAL '30 days'" if is_postgres else "AND q.created_at >= date('now', '-30 days')"
            elif period == 'quarter':
                date_filter = "AND q.created_at >= CURRENT_DATE - INTERVAL '90 days'" if is_postgres else "AND q.created_at >= date('now', '-90 days')"
            elif period == 'year':
                date_filter = "AND q.created_at >= CURRENT_DATE - INTERVAL '365 days'" if is_postgres else "AND q.created_at >= date('now', '-365 days')"
            
            if metric == 'quote_count':
                cursor.execute(f"""
                    SELECT 
                        u.id as analyst_id,
                        u.full_name as analyst_name,
                        COUNT(q.id) as metric_value
                    FROM users u
                    LEFT JOIN quotes q ON u.id = q.analyst_id {date_filter.replace('AND', 'WHERE') if date_filter else ''}
                    WHERE u.role = 'analyst'
                    GROUP BY u.id, u.full_name
                    ORDER BY metric_value DESC
                    LIMIT {'%s' if is_postgres else '?'}
                """, (limit,))
            elif metric == 'total_amount':
                cursor.execute(f"""
                    SELECT 
                        u.id as analyst_id,
                        u.full_name as analyst_name,
                        COALESCE(SUM(q.total_amount), 0) as metric_value
                    FROM users u
                    LEFT JOIN quotes q ON u.id = q.analyst_id {date_filter.replace('AND', 'WHERE') if date_filter else ''}
                    WHERE u.role = 'analyst'
                    GROUP BY u.id, u.full_name
                    ORDER BY metric_value DESC
                    LIMIT {'%s' if is_postgres else '?'}
                """, (limit,))
            elif metric == 'approval_rate':
                # Calcular tasa de aprobación por analista
                cursor.execute(f"""
                    SELECT 
                        u.id as analyst_id,
                        u.full_name as analyst_name,
                        CASE 
                            WHEN COUNT(CASE WHEN q.status IN ('approved', 'rejected', 'sent') THEN 1 END) > 0
                            THEN (COUNT(CASE WHEN q.status = 'approved' THEN 1 END) * 100.0 / 
                                  COUNT(CASE WHEN q.status IN ('approved', 'rejected', 'sent') THEN 1 END))
                            ELSE 0
                        END as metric_value
                    FROM users u
                    LEFT JOIN quotes q ON u.id = q.analyst_id {date_filter.replace('AND', 'WHERE') if date_filter else ''}
                    WHERE u.role = 'analyst'
                    GROUP BY u.id, u.full_name
                    ORDER BY metric_value DESC
                    LIMIT {'%s' if is_postgres else '?'}
                """, (limit,))
            
            ranking = []
            for row in cursor.fetchall():
                ranking.append({
                    'analyst_id': row['analyst_id'] if is_postgres else row[0],
                    'analyst_name': row['analyst_name'] if is_postgres else row[1],
                    'metric_value': float(row['metric_value'] if is_postgres else row[2])
                })
            
            cursor.close()
            conn.close()
            
            return ranking
            
        except Exception as e:
            print(f"❌ Error al obtener ranking de analistas: {e}")
            return []

    @staticmethod
    def update_quote_complete(quote_id: int, cliente_datos: Dict[str, Any], items: List[Dict[str, Any]], username: str) -> bool:
        """
        Actualiza una cotización completa (datos del cliente + ítems).
        Función wrapper que llama a update_quote() y update_quote_items().
        
        Args:
            quote_id: ID de la cotización a actualizar
            cliente_datos: Diccionario con los datos del cliente
            items: Lista de diccionarios con los ítems
            username: Nombre de usuario que realiza la edición
            
        Returns:
            True si se actualizó exitosamente, False en caso de error
        """
        try:
            # Obtener user_id desde username
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT id FROM users WHERE username = %s
            """ if is_postgres else """
                SELECT id FROM users WHERE username = ?
            """, (username,))
            
            user_result = cursor.fetchone()
            if not user_result:
                print(f"❌ Usuario {username} no encontrado")
                cursor.close()
                conn.close()
                return False
            
            user_id = user_result['id'] if is_postgres else user_result[0]
            cursor.close()
            conn.close()
            
            # Preparar datos para update_quote
            quote_data = {
                'client_name': cliente_datos.get('nombre', ''),
                'client_phone': cliente_datos.get('telefono', ''),
                'client_email': cliente_datos.get('email', ''),
                'client_cedula': cliente_datos.get('ci_rif', ''),
                'client_address': cliente_datos.get('direccion', ''),
                'client_vehicle': cliente_datos.get('vehiculo', ''),
                'client_year': cliente_datos.get('ano', ''),
                'client_vin': cliente_datos.get('vin', ''),
            }
            
            # Actualizar datos del cliente
            success_cliente = DBManager.update_quote(quote_id, quote_data, user_id)
            if not success_cliente:
                print(f"❌ Error al actualizar datos del cliente")
                return False
            
            # Actualizar ítems
            success_items = DBManager.update_quote_items(quote_id, items, user_id)
            if not success_items:
                print(f"❌ Error al actualizar ítems")
                return False
            
            print(f"✅ Cotización {quote_id} actualizada completamente")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar cotización completa: {e}")
            import traceback
            traceback.print_exc()
            return False

