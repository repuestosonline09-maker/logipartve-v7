# database/quote_search.py
# Funciones de búsqueda de cotizaciones

from typing import Optional, List, Dict, Any
from database.db_manager import DBManager

class QuoteSearch:
    """Clase para búsqueda de cotizaciones"""
    
    @staticmethod
    def search_by_quote_number(quote_number: str) -> Optional[Dict[str, Any]]:
        """
        Busca una cotización por su número.
        
        Args:
            quote_number: Número de cotización (ej: "2026-30000-A")
            
        Returns:
            Dict con los datos de la cotización, o None si no se encuentra
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.quote_number = %s
            """ if is_postgres else """
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.quote_number = ?
            """, (quote_number,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"Error al buscar cotización: {e}")
            return None
    
    @staticmethod
    def search_by_analyst(analyst_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene las cotizaciones de un analista específico.
        
        Args:
            analyst_id: ID del analista
            limit: Número máximo de resultados
            
        Returns:
            Lista de cotizaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.analyst_id = %s
                ORDER BY q.created_at DESC
                LIMIT %s
            """ if is_postgres else """
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.analyst_id = ?
                ORDER BY q.created_at DESC
                LIMIT ?
            """, (analyst_id, limit))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return quotes
            
        except Exception as e:
            print(f"Error al buscar cotizaciones del analista: {e}")
            return []
    
    @staticmethod
    def search_by_client_name(client_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca cotizaciones por nombre de cliente (búsqueda parcial).
        
        Args:
            client_name: Nombre del cliente (o parte del nombre)
            limit: Número máximo de resultados
            
        Returns:
            Lista de cotizaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            # Búsqueda parcial con LIKE
            search_pattern = f"%{client_name}%"
            
            cursor.execute("""
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.client_name ILIKE %s
                ORDER BY q.created_at DESC
                LIMIT %s
            """ if is_postgres else """
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                WHERE q.client_name LIKE ?
                ORDER BY q.created_at DESC
                LIMIT ?
            """, (search_pattern, limit))
            
            quotes = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return quotes
            
        except Exception as e:
            print(f"Error al buscar cotizaciones por cliente: {e}")
            return []
    
    @staticmethod
    def get_all_quotes(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene todas las cotizaciones ordenadas por fecha.
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de cotizaciones
        """
        try:
            conn = DBManager.get_connection()
            cursor = conn.cursor()
            is_postgres = DBManager.USE_POSTGRES
            
            cursor.execute("""
                SELECT q.*, u.username, u.full_name
                FROM quotes q
                JOIN users u ON q.analyst_id = u.id
                ORDER BY q.created_at DESC
                LIMIT %s
            """ if is_postgres else """
                SELECT q.*, u.username, u.full_name
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
            print(f"Error al obtener cotizaciones: {e}")
            return []
