# database/db_manager.py
# Gestor de base de datos SQLite (preparado para migración a PostgreSQL)

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import bcrypt

class DBManager:
    """
    Gestor de base de datos para LogiPartVE Pro v7.0
    Maneja 7 tablas: users, system_config, quotes, quote_items, pages, cache, activity_logs
    """
    
    DB_PATH = Path(__file__).parent / "logipartve.db"
    
    @staticmethod
    def get_connection():
        """Crea y retorna una conexión a la base de datos."""
        conn = sqlite3.connect(str(DBManager.DB_PATH))
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        return conn
    
    @staticmethod
    def init_database():
        """Inicializa todas las tablas de la base de datos."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Tabla 1: users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'analyst')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Tabla 2: system_config
        cursor.execute("""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quote_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                origin TEXT NOT NULL CHECK(origin IN ('Miami', 'Madrid')),
                active INTEGER DEFAULT 1
            )
        """)
        
        # Tabla 6: cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tabla 8: freight_rates (tarifas de flete)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freight_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        if cursor.fetchone()[0] == 0:
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            """, ("admin", password_hash, "Administrador", "admin"))
            conn.commit()
        
        # Insertar configuraciones por defecto si no existen
        default_configs = [
            ("exchange_differential", "45", "Diferencial BCV vs Paralelo - Porcentaje diario"),
            ("american_tax", "7", "TAX de empresa americana - Porcentaje (valor único, no seleccionable)"),
            ("national_handling", "18", "Costo de manejo nacional - Dólares"),
            ("venezuela_iva", "16", "IVA Venezuela - Porcentaje"),
            ("profit_factors", "1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0", "Factores de utilidad disponibles (separados por coma)"),
            ("warranties", "15 DIAS,30 DIAS,45 DIAS,3 MESES,6 MESES", "Opciones de garantía (separadas por coma)"),
            ("terms_conditions", "Términos y condiciones estándar de LogiPartVE Pro", "Términos y condiciones de las cotizaciones"),
            ("manejo_options", "0,15,23,25", "Opciones de MANEJO en dólares (separadas por coma)"),
            ("impuesto_internacional_options", "0,25,30,35,40,45,50", "Opciones de Impuesto Internacional % (separadas por coma)"),
            ("paises_origen", "EEUU,MIAMI,ESPAÑA,MADRID,ALEMANIA,ARGENTINA,ARUBA,AUSTRALIA,BRASIL,CANADA,CHILE,CHINA,COLOMBIA,COREA DEL SUR,DINAMARCA,DUBAI,ESTONIA,FRANCIA,GRECIA,HOLANDA,HUNGRIA,INDIA,INDONESIA,INGLATERRA,IRLANDA,ITALIA,JAPÓN,JORDANIA,LETONIA,LITUANIA,MALASIA,MEXICO,POLONIA,PORTUGAL,PUERTO RICO,REINO UNIDO,SINGAPUR,TAILANDIA,TAIWAN,TURQUIA,UCRANIA,UNION EUROPEA,VARIOS,VENEZUELA", "Países de origen/localización (separados por coma)"),
            ("tipos_envio", "AEREO,MARITIMO,TERRESTRE", "Tipos de envío disponibles (separados por coma)"),
            ("tiempos_entrega", "02 A 05 DIAS,08 A 12 DIAS,12 A 15 DIAS,18 A 21 DIAS,25 A 30 DIAS,30 A 45 DIAS,60 DIAS", "Tiempos de entrega disponibles (separados por coma)")
        ]
        
        for key, value, description in default_configs:
            cursor.execute("SELECT COUNT(*) FROM system_config WHERE key = ?", (key,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO system_config (key, value, description)
                    VALUES (?, ?, ?)
                """, (key, value, description))
        
        # Insertar tarifas de flete por defecto si no existen
        default_freight_rates = [
            ("Miami", "Aéreo", 9.0, "$/lb"),
            ("Miami", "Marítimo", 40.0, "$/ft³"),
            ("Madrid", "Aéreo", 25.0, "$/kg")
        ]
        
        for origin, shipping_type, rate, unit in default_freight_rates:
            cursor.execute(
                "SELECT COUNT(*) FROM freight_rates WHERE origin = ? AND shipping_type = ?",
                (origin, shipping_type)
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO freight_rates (origin, shipping_type, rate, unit)
                    VALUES (?, ?, ?, ?)
                """, (origin, shipping_type, rate, unit))
        
        conn.commit()
        conn.close()
    
    # ========== MÉTODOS PARA USERS ==========
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """Obtiene un usuario por su nombre de usuario."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict]:
        """Obtiene un usuario por su ID."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """Obtiene todos los usuarios."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, created_at, last_login FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def create_user(username: str, password: str, full_name: str, role: str) -> bool:
        """Crea un nuevo usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, full_name, role))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    @staticmethod
    def update_user(user_id: int, full_name: str = None, role: str = None) -> bool:
        """Actualiza información de un usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if full_name:
                updates.append("full_name = ?")
                params.append(full_name)
            
            if role:
                updates.append("role = ?")
                params.append(role)
            
            if not updates:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def change_password(user_id: int, new_password: str) -> bool:
        """Cambia la contraseña de un usuario."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Elimina un usuario (solo si no es el admin principal)."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            # No permitir eliminar al admin principal
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if user and user['username'] == 'admin':
                return False
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    @staticmethod
    def update_last_login(user_id: int):
        """Actualiza la fecha de último login."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now(), user_id))
        conn.commit()
        conn.close()
    
    # ========== MÉTODOS PARA SYSTEM_CONFIG ==========
    
    @staticmethod
    def get_config(key: str) -> Optional[str]:
        """Obtiene un valor de configuración."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else None
    
    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        """Obtiene todas las configuraciones."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, description FROM system_config")
        rows = cursor.fetchall()
        conn.close()
        return {row['key']: {'value': row['value'], 'description': row['description']} for row in rows}
    
    @staticmethod
    def update_config(key: str, value: str, updated_by: int = None) -> bool:
        """Actualiza un valor de configuración."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_config 
                SET value = ?, updated_by = ?, updated_at = ?
                WHERE key = ?
            """, (value, updated_by, datetime.now(), key))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    # ========== MÉTODOS PARA ACTIVITY_LOGS ==========
    
    @staticmethod
    def log_activity(user_id: int, action: str, details: str = None):
        """Registra una actividad en el log."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (user_id, action, details)
            VALUES (?, ?, ?)
        """, (user_id, action, details))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_recent_activities(limit: int = 50) -> List[Dict]:
        """Obtiene las actividades recientes."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT al.*, u.username, u.full_name
            FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            ORDER BY al.timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ========== MÉTODOS PARA QUOTES (para reportes) ==========
    
    @staticmethod
    def get_quotes_by_analyst(analyst_id: int) -> List[Dict]:
        """Obtiene todas las cotizaciones de un analista."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM quotes 
            WHERE analyst_id = ?
            ORDER BY created_at DESC
        """, (analyst_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_quotes_by_period(start_date: str, end_date: str) -> List[Dict]:
        """Obtiene cotizaciones por período."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.*, u.username, u.full_name
            FROM quotes q
            JOIN users u ON q.analyst_id = u.id
            WHERE DATE(q.created_at) BETWEEN ? AND ?
            ORDER BY q.created_at DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_quote_stats() -> Dict:
        """Obtiene estadísticas generales de cotizaciones."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Total de cotizaciones
        cursor.execute("SELECT COUNT(*) as total FROM quotes")
        total = cursor.fetchone()['total']
        
        # Cotizaciones por estado
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM quotes 
            GROUP BY status
        """)
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Cotizaciones por analista
        cursor.execute("""
            SELECT u.full_name, COUNT(q.id) as count
            FROM users u
            LEFT JOIN quotes q ON u.id = q.analyst_id
            WHERE u.role = 'analyst'
            GROUP BY u.id, u.full_name
        """)
        by_analyst = {row['full_name']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total': total,
            'by_status': by_status,
            'by_analyst': by_analyst
        }

    # ========== MÉTODOS PARA FREIGHT_RATES ==========
    
    @staticmethod
    def get_all_freight_rates() -> List[Dict]:
        """Obtiene todas las tarifas de flete."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, origin, shipping_type, rate, unit, updated_at
            FROM freight_rates
            ORDER BY origin, shipping_type
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_freight_rate(origin: str, shipping_type: str) -> Optional[float]:
        """Obtiene la tarifa de flete para un origen y tipo de envío específico."""
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rate FROM freight_rates 
            WHERE origin = ? AND shipping_type = ?
        """, (origin, shipping_type))
        row = cursor.fetchone()
        conn.close()
        return row['rate'] if row else None
    
    @staticmethod
    def update_freight_rate(origin: str, shipping_type: str, rate: float, updated_by: int = None) -> bool:
        """Actualiza una tarifa de flete."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE freight_rates 
                SET rate = ?, updated_by = ?, updated_at = ?
                WHERE origin = ? AND shipping_type = ?
            """, (rate, updated_by, datetime.now(), origin, shipping_type))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating freight rate: {e}")
            return False


    # ========== MÉTODOS HELPER PARA LISTAS DE CONFIGURACIÓN ==========
    
    @staticmethod
    def get_config_list(key: str) -> List[str]:
        """Obtiene una lista de configuración separada por comas."""
        value = DBManager.get_config(key)
        if value:
            return [item.strip() for item in value.split(',') if item.strip()]
        return []
    
    @staticmethod
    def get_manejo_options() -> List[float]:
        """Obtiene las opciones de MANEJO configuradas."""
        items = DBManager.get_config_list("manejo_options")
        try:
            return [float(x) for x in items]
        except:
            return [0.0, 15.0, 23.0, 25.0]
    
    @staticmethod
    def get_impuesto_internacional_options() -> List[int]:
        """Obtiene las opciones de Impuesto Internacional configuradas."""
        items = DBManager.get_config_list("impuesto_internacional_options")
        try:
            return [int(x) for x in items]
        except:
            return [0, 25, 30, 35, 40, 45, 50]
    
    @staticmethod
    def get_profit_factors() -> List[float]:
        """Obtiene los factores de utilidad configurados."""
        items = DBManager.get_config_list("profit_factors")
        try:
            return [float(x) for x in items]
        except:
            return [1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 0]
    
    @staticmethod
    def get_tax_percentage() -> float:
        """Obtiene el porcentaje de TAX configurado."""
        value = DBManager.get_config("american_tax")
        try:
            return float(value) if value else 7.0
        except:
            return 7.0
    
    @staticmethod
    def get_warranties() -> List[str]:
        """Obtiene las opciones de garantía configuradas."""
        items = DBManager.get_config_list("warranties")
        return items if items else ["15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES"]
    
    @staticmethod
    def get_paises_origen() -> List[str]:
        """Obtiene la lista de países de origen configurados."""
        items = DBManager.get_config_list("paises_origen")
        return items if items else ["EEUU", "MIAMI", "ESPAÑA", "MADRID"]
    
    @staticmethod
    def get_tipos_envio() -> List[str]:
        """Obtiene los tipos de envío configurados."""
        items = DBManager.get_config_list("tipos_envio")
        return items if items else ["AEREO", "MARITIMO", "TERRESTRE"]
    
    @staticmethod
    def get_tiempos_entrega() -> List[str]:
        """Obtiene los tiempos de entrega configurados."""
        items = DBManager.get_config_list("tiempos_entrega")
        return items if items else ["02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS"]
    
    @staticmethod
    def get_diferencial() -> float:
        """Obtiene el diferencial de cambio configurado (BCV vs Paralelo)."""
        value = DBManager.get_config("exchange_differential")
        try:
            return float(value) if value else 45.0
        except:
            return 45.0
    
    @staticmethod
    def get_iva_venezuela() -> float:
        """Obtiene el porcentaje de IVA Venezuela configurado."""
        value = DBManager.get_config("venezuela_iva")
        try:
            return float(value) if value else 16.0
        except:
            return 16.0
    
    @staticmethod
    def set_config(key: str, value: str, description: str = None, updated_by: int = None) -> bool:
        """Crea o actualiza un valor de configuración."""
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute("SELECT COUNT(*) FROM system_config WHERE key = ?", (key,))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute("""
                    UPDATE system_config 
                    SET value = ?, updated_by = ?, updated_at = ?
                    WHERE key = ?
                """, (value, updated_by, datetime.now(), key))
            else:
                cursor.execute("""
                    INSERT INTO system_config (key, value, description, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, value, description or "", updated_by, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error setting config: {e}")
            return False
