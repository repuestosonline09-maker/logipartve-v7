"""
Servicio para parsear respuestas de IA
Extrae datos estructurados de las respuestas de texto
"""
import re


class AIParser:
    """Parser de respuestas de IA"""
    
    def parse_response(self, response_text: str) -> dict:
        """
        Parsea la respuesta de la IA y extrae datos estructurados
        
        Args:
            response_text: Texto de respuesta de la IA
        
        Returns:
            dict: Datos estructurados extraídos
        """
        result = {
            'descripcion': '',
            'numero_parte_original': '',
            'numeros_parte_alternativos': [],
            'peso_kg': None,
            'dimensiones': {
                'largo_cm': None,
                'ancho_cm': None,
                'alto_cm': None
            },
            'embalaje': {
                'largo_cm': None,
                'ancho_cm': None,
                'alto_cm': None
            },
            'peso_volumetrico': None,
            'sitios_consultados': [],
            'nivel_confianza': '',
            'requiere_validacion_manual': False,
            'notas_tecnicas': '',
            'raw_response': response_text
        }
        
        # Extraer descripción
        desc_match = re.search(r'DESCRIPCIÓN[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)', response_text, re.DOTALL)
        if desc_match:
            result['descripcion'] = desc_match.group(1).strip()
        
        # Extraer número de parte
        part_match = re.search(r'NÚMERO DE PARTE[:\s]+([A-Z0-9-]+)', response_text)
        if part_match:
            result['numero_parte_original'] = part_match.group(1).strip()
        
        # Extraer alternativos
        alt_match = re.search(r'ALTERNATIVOS[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)', response_text, re.DOTALL)
        if alt_match:
            alts = re.findall(r'[A-Z0-9-]+', alt_match.group(1))
            result['numeros_parte_alternativos'] = alts
        
        # Extraer peso
        peso_match = re.search(r'PESO[:\s]+([\d.]+)\s*kg', response_text, re.IGNORECASE)
        if peso_match:
            result['peso_kg'] = float(peso_match.group(1))
        
        # Extraer dimensiones
        dim_match = re.search(r'DIMENSIONES[:\s]+([\d.]+)\s*×\s*([\d.]+)\s*×\s*([\d.]+)\s*cm', response_text, re.IGNORECASE)
        if dim_match:
            result['dimensiones'] = {
                'largo_cm': float(dim_match.group(1)),
                'ancho_cm': float(dim_match.group(2)),
                'alto_cm': float(dim_match.group(3))
            }
        
        # Extraer embalaje
        emb_match = re.search(r'EMBALAJE[:\s]+([\d.]+)\s*×\s*([\d.]+)\s*×\s*([\d.]+)\s*cm', response_text, re.IGNORECASE)
        if emb_match:
            result['embalaje'] = {
                'largo_cm': float(emb_match.group(1)),
                'ancho_cm': float(emb_match.group(2)),
                'alto_cm': float(emb_match.group(3))
            }
        
        # Detectar validación manual requerida
        if 'VALIDACIÓN MANUAL REQUERIDA' in response_text or 'VALIDACION MANUAL REQUERIDA' in response_text:
            result['requiere_validacion_manual'] = True
        
        # Extraer sitios consultados
        sitios_match = re.search(r'SITIOS CONSULTADOS[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)', response_text, re.DOTALL)
        if sitios_match:
            sitios = re.findall(r'[\w.-]+\.(?:com|es|asia)', sitios_match.group(1))
            result['sitios_consultados'] = sitios
        
        # Extraer nivel de confianza
        conf_match = re.search(r'CONFIANZA[:\s]+(ALTA|MEDIA|BAJA)', response_text, re.IGNORECASE)
        if conf_match:
            result['nivel_confianza'] = conf_match.group(1).upper()
        
        return result
    
    def validate_response(self, parsed_data: dict) -> dict:
        """
        Valida que la respuesta parseada tenga datos mínimos
        
        Args:
            parsed_data: Datos parseados de la respuesta
        
        Returns:
            dict: {
                'valid': bool,
                'missing_fields': list,
                'warnings': list
            }
        """
        missing = []
        warnings = []
        
        # Campos críticos
        if not parsed_data['descripcion']:
            missing.append('descripcion')
        
        if not parsed_data['peso_kg']:
            missing.append('peso_kg')
        
        if not any(parsed_data['dimensiones'].values()):
            missing.append('dimensiones')
        
        # Advertencias
        if parsed_data['requiere_validacion_manual']:
            warnings.append('Requiere validación manual')
        
        if not parsed_data['sitios_consultados']:
            warnings.append('No se especificaron sitios consultados')
        
        if not parsed_data['nivel_confianza']:
            warnings.append('No se especificó nivel de confianza')
        
        return {
            'valid': len(missing) == 0,
            'missing_fields': missing,
            'warnings': warnings
        }
