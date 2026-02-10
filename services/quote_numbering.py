# services/quote_numbering.py
# Servicio de numeración automática de cotizaciones

from datetime import datetime
from typing import Optional, Dict, Any
from database.db_manager import DBManager

class QuoteNumberingService:
    """
    Servicio para generar números de cotización automáticos.
    
    Formato: [AÑO]-[NÚMERO]-[INICIAL]
    Ejemplo: 2026-30000-A (Admin), 2026-40001-J (Juan)
    
    Rangos por usuario:
    - Usuario 1: 30000-39999
    - Usuario 2: 40000-49999
    - Usuario 3: 50000-59999
    - Usuario 4: 60000-69999
    - Usuario 5: 70000-79999
    """
    
    @staticmethod
    def assign_range_to_new_user(user_id: int) -> bool:
        """
        Asigna un rango de numeración a un nuevo usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            bool: True si se asignó correctamente, False si no hay rangos disponibles
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Verificar si el usuario ya tiene rango
            cursor.execute("""
                SELECT COUNT(*) FROM user_quote_ranges WHERE user_id = %s
            """ if is_postgres else """
                SELECT COUNT(*) FROM user_quote_ranges WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            count = result['count'] if is_postgres else result[0]
            
            if count > 0:
                cursor.close()
                conn.close()
                return True  # Ya tiene rango asignado
            
            # Obtener todos los usuarios ordenados por ID
            cursor.execute("SELECT id FROM users ORDER BY id ASC")
            all_users = [row['id'] if is_postgres else row[0] for row in cursor.fetchall()]
            
            # Encontrar la posición del usuario
            try:
                user_position = all_users.index(user_id)
            except ValueError:
                cursor.close()
                conn.close()
                return False
            
            # Rangos disponibles
            base_ranges = [30000, 40000, 50000, 60000, 70000]
            
            if user_position >= len(base_ranges):
                cursor.close()
                conn.close()
                return False  # No hay más rangos disponibles
            
            range_start = base_ranges[user_position]
            range_end = range_start + 9999
            
            # Asignar rango
            cursor.execute("""
                INSERT INTO user_quote_ranges (user_id, range_start, range_end)
                VALUES (%s, %s, %s)
            """ if is_postgres else """
                INSERT INTO user_quote_ranges (user_id, range_start, range_end)
                VALUES (?, ?, ?)
            """, (user_id, range_start, range_end))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error al asignar rango: {e}")
            return False
    
    @staticmethod
    def get_user_range(user_id: int) -> Optional[Dict[str, int]]:
        """
        Obtiene el rango asignado a un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con 'range_start' y 'range_end', o None si no tiene rango
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT range_start, range_end FROM user_quote_ranges WHERE user_id = %s
            """ if is_postgres else """
                SELECT range_start, range_end FROM user_quote_ranges WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return {
                    'range_start': result['range_start'] if is_postgres else result[0],
                    'range_end': result['range_end'] if is_postgres else result[1]
                }
            return None
            
        except Exception as e:
            print(f"Error al obtener rango: {e}")
            return None
    
    @staticmethod
    def generate_quote_number(user_id: int, username: str) -> Optional[str]:
        """
        Genera el siguiente número de cotización para un usuario.
        
        Args:
            user_id: ID del usuario
            username: Nombre de usuario (para obtener la inicial)
            
        Returns:
            str: Número de cotización (ej: "2026-30000-A")
            None: Si hay algún error
        """
        try:
            # Asegurarse de que el usuario tenga rango asignado
            user_range = QuoteNumberingService.get_user_range(user_id)
            if not user_range:
                # Intentar asignar rango
                if not QuoteNumberingService.assign_range_to_new_user(user_id):
                    return None
                user_range = QuoteNumberingService.get_user_range(user_id)
                if not user_range:
                    return None
            
            # Obtener año actual
            current_year = datetime.now().year
            
            # Obtener la inicial del usuario (primera letra del username en mayúscula)
            initial = username[0].upper() if username else 'X'
            
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Obtener la última secuencia del usuario para este año
            cursor.execute("""
                SELECT last_number FROM quote_sequences 
                WHERE user_id = %s AND year = %s
            """ if is_postgres else """
                SELECT last_number FROM quote_sequences 
                WHERE user_id = ? AND year = ?
            """, (user_id, current_year))
            
            result = cursor.fetchone()
            
            if result:
                # Ya existe una secuencia para este año, incrementar
                last_number = result['last_number'] if is_postgres else result[0]
                next_number = last_number + 1
                
                # Verificar que no exceda el rango
                if next_number > user_range['range_end']:
                    cursor.close()
                    conn.close()
                    return None  # Rango agotado
                
                # Actualizar secuencia
                cursor.execute("""
                    UPDATE quote_sequences 
                    SET last_number = %s 
                    WHERE user_id = %s AND year = %s
                """ if is_postgres else """
                    UPDATE quote_sequences 
                    SET last_number = ? 
                    WHERE user_id = ? AND year = ?
                """, (next_number, user_id, current_year))
            else:
                # Primera cotización del año, empezar desde el inicio del rango
                next_number = user_range['range_start']
                
                # Crear nueva secuencia
                cursor.execute("""
                    INSERT INTO quote_sequences (user_id, year, last_number)
                    VALUES (%s, %s, %s)
                """ if is_postgres else """
                    INSERT INTO quote_sequences (user_id, year, last_number)
                    VALUES (?, ?, ?)
                """, (user_id, current_year, next_number))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Formatear número: [AÑO]-[NÚMERO]-[INICIAL]
            quote_number = f"{current_year}-{next_number:05d}-{initial}"
            return quote_number
            
        except Exception as e:
            print(f"Error al generar número de cotización: {e}")
            return None
    
    @staticmethod
    def get_next_quote_number_preview(user_id: int, username: str) -> Optional[str]:
        """
        Obtiene una vista previa del siguiente número de cotización SIN incrementar la secuencia.
        Útil para mostrar en la interfaz antes de guardar la cotización.
        
        Args:
            user_id: ID del usuario
            username: Nombre de usuario
            
        Returns:
            str: Número de cotización (ej: "2026-30000-A")
        """
        try:
            user_range = QuoteNumberingService.get_user_range(user_id)
            if not user_range:
                if not QuoteNumberingService.assign_range_to_new_user(user_id):
                    return None
                user_range = QuoteNumberingService.get_user_range(user_id)
                if not user_range:
                    return None
            
            current_year = datetime.now().year
            initial = username[0].upper() if username else 'X'
            
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT last_number FROM quote_sequences 
                WHERE user_id = %s AND year = %s
            """ if is_postgres else """
                SELECT last_number FROM quote_sequences 
                WHERE user_id = ? AND year = ?
            """, (user_id, current_year))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                next_number = (result['last_number'] if is_postgres else result[0]) + 1
            else:
                next_number = user_range['range_start']
            
            quote_number = f"{current_year}-{next_number:05d}-{initial}"
            return quote_number
            
        except Exception as e:
            print(f"Error al obtener vista previa: {e}")
            return None
