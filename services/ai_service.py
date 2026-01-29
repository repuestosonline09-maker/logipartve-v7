"""
Servicio de IA para análisis de repuestos
Integra Gemini (primario) y OpenAI (fallback)
"""
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai no está instalado")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai no está instalado")

from prompts.omni_parts_prompt import (
    get_omni_parts_prompt_with_url,
    get_omni_parts_prompt_without_url
)


class AIService:
    """Servicio de IA con Gemini y OpenAI fallback"""
    
    def __init__(self):
        # Configurar Gemini
        self.gemini_model = None
        if GEMINI_AVAILABLE:
            self.gemini_api_key = os.getenv('GEMINI_API_KEY')
            if self.gemini_api_key:
                try:
                    genai.configure(api_key=self.gemini_api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                except Exception as e:
                    print(f"Error configurando Gemini: {str(e)}")
        
        # Configurar OpenAI
        self.openai_client = None
        if OPENAI_AVAILABLE:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if self.openai_api_key:
                try:
                    self.openai_client = OpenAI(api_key=self.openai_api_key)
                except Exception as e:
                    print(f"Error configurando OpenAI: {str(e)}")
    
    def analyze_part_with_url(self, vehiculo: str, repuesto: str, 
                             numero_parte: str, url: str, 
                             origen: str, envio: str) -> dict:
        """
        Analiza un repuesto con URL proporcionada
        
        Args:
            vehiculo: Modelo del vehículo
            repuesto: Nombre del repuesto
            numero_parte: Número de parte
            url: URL del producto
            origen: Puerto de origen
            envio: Tipo de envío
        
        Returns:
            dict: {
                'success': bool,
                'response': str,
                'provider': str,  # 'gemini' o 'openai'
                'error': str (opcional)
            }
        """
        prompt = get_omni_parts_prompt_with_url(
            vehiculo, repuesto, numero_parte, url, origen, envio
        )
        
        return self._generate_response(prompt)
    
    def analyze_part_without_url(self, vehiculo: str, repuesto: str,
                                 numero_parte: str, origen: str, 
                                 envio: str) -> dict:
        """
        Analiza un repuesto sin URL (búsqueda en lista blanca)
        
        Args:
            vehiculo: Modelo del vehículo
            repuesto: Nombre del repuesto
            numero_parte: Número de parte
            origen: Puerto de origen
            envio: Tipo de envío
        
        Returns:
            dict: {
                'success': bool,
                'response': str,
                'provider': str,
                'error': str (opcional)
            }
        """
        prompt = get_omni_parts_prompt_without_url(
            vehiculo, repuesto, numero_parte, origen, envio
        )
        
        return self._generate_response(prompt)
    
    def _generate_response(self, prompt: str) -> dict:
        """
        Genera respuesta usando Gemini o OpenAI
        
        Args:
            prompt: Prompt completo para la IA
        
        Returns:
            dict: Resultado de la generación
        """
        # Intentar con Gemini primero
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return {
                    'success': True,
                    'response': response.text,
                    'provider': 'gemini'
                }
            except Exception as e:
                print(f"Error con Gemini: {str(e)}")
                # Continuar con OpenAI
        
        # Fallback a OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un experto en repuestos automotrices y logística."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                return {
                    'success': True,
                    'response': response.choices[0].message.content,
                    'provider': 'openai'
                }
            except Exception as e:
                return {
                    'success': False,
                    'response': '',
                    'provider': 'none',
                    'error': f"Error con OpenAI: {str(e)}"
                }
        
        return {
            'success': False,
            'response': '',
            'provider': 'none',
            'error': 'No hay servicios de IA configurados'
        }
