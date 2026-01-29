"""
Servicio de validación de URLs contra lista blanca
"""
import re
from urllib.parse import urlparse
import sys
import os

# Agregar el directorio padre al path para importar prompts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.omni_parts_prompt import WHITELIST_SITES


class URLValidator:
    """Valida URLs contra la lista blanca de sitios autorizados"""
    
    def __init__(self):
        self.whitelist = WHITELIST_SITES
    
    def is_valid_url(self, url: str) -> bool:
        """
        Valida el formato de una URL
        
        Args:
            url: URL a validar
        
        Returns:
            bool: True si el formato es válido
        """
        pattern = re.compile(
            r'^https?://'  # http:// o https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # dominio
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...o IP
            r'(?::\d+)?'  # puerto opcional
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return pattern.match(url) is not None
    
    def get_domain(self, url: str) -> str:
        """
        Extrae el dominio de una URL
        
        Args:
            url: URL completa
        
        Returns:
            str: Dominio extraído (sin www.)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain
        except Exception:
            return ''
    
    def is_whitelisted(self, url: str) -> bool:
        """
        Verifica si la URL está en la lista blanca
        
        Args:
            url: URL a verificar
        
        Returns:
            bool: True si está en lista blanca
        """
        domain = self.get_domain(url)
        return any(site in domain for site in self.whitelist)
    
    def validate(self, url: str) -> dict:
        """
        Valida una URL completamente
        
        Args:
            url: URL a validar
        
        Returns:
            dict: {
                'valid': bool,
                'whitelisted': bool,
                'domain': str,
                'message': str
            }
        """
        if not url:
            return {
                'valid': False,
                'whitelisted': False,
                'domain': '',
                'message': 'URL vacía'
            }
        
        if not self.is_valid_url(url):
            return {
                'valid': False,
                'whitelisted': False,
                'domain': '',
                'message': 'Formato de URL inválido'
            }
        
        domain = self.get_domain(url)
        whitelisted = self.is_whitelisted(url)
        
        if not whitelisted:
            return {
                'valid': True,
                'whitelisted': False,
                'domain': domain,
                'message': f'El dominio {domain} no está en la lista blanca'
            }
        
        return {
            'valid': True,
            'whitelisted': True,
            'domain': domain,
            'message': 'URL válida y autorizada'
        }
