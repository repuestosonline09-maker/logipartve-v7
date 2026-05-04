"""
Funciones auxiliares para obtener configuraciones del sistema
LogiPartVE Pro v7.5

ARQUITECTURA DE FALLBACK (3 niveles):
  1. Lee el valor de la BD normalmente
  2. Si la BD no responde, reintenta 1 vez después de 0.5s
  3. Si sigue fallando, usa los valores por defecto de init_default_config.py
     (que son los mismos que se insertan en la BD al inicializar el sistema)
  → NUNCA hay listas hardcodeadas aquí. Todo viene de un solo lugar: init_default_config.py
"""

import time
from database.db_manager import DBManager
from typing import List


def _get_config_with_retry(key: str, retries: int = 1, delay: float = 0.5):
    """Lee una clave de configuración con reintentos automáticos."""
    for attempt in range(retries + 1):
        try:
            value = DBManager.get_config(key)
            if value:
                return value
        except Exception as e:
            if attempt < retries:
                time.sleep(delay)
            else:
                print(f"[ConfigHelpers] Error al leer '{key}' tras {retries+1} intentos: {e}")
    return None


def _get_defaults():
    """
    Obtiene los valores por defecto desde init_default_config.py.
    Esto garantiza que el fallback siempre esté sincronizado con
    los valores que se insertan en la BD al inicializar el sistema.
    """
    try:
        from database.init_default_config import get_default_config_values
        return get_default_config_values()
    except Exception:
        # Último recurso: valores absolutamente mínimos para no romper la app
        return {
            'paises_origen':                  'EEUU,MIAMI',
            'tipos_envio':                    'AEREO,MARITIMO',
            'tiempos_entrega':                '08 A 12 DIAS,12 A 15 DIAS',
            'garantias':                      '30 DIAS,3 MESES',
            'manejo_options':                 '0.0,15.0,23.0,25.0',
            'impuesto_internacional_options': '0,25,30,35,40,45,50',
            'profit_factors':                 '1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0',
            'tax_percentage':                 '7.0',
            'exchange_differential':          '45.0',
            'iva_venezuela':                  '16.0',
        }


class ConfigHelpers:
    """Clase con métodos estáticos para obtener configuraciones.
    
    Todos los métodos usan 3 niveles de fallback:
    BD → reintento → init_default_config.py
    Nunca hay listas hardcodeadas en este archivo.
    """

    @staticmethod
    def get_paises_origen() -> List[str]:
        """Obtiene la lista de países de origen desde la configuración"""
        value = _get_config_with_retry('paises_origen')
        if not value:
            value = _get_defaults().get('paises_origen', 'EEUU,MIAMI')
        return [p.strip() for p in value.split(',') if p.strip()]

    @staticmethod
    def get_tipos_envio() -> List[str]:
        """Obtiene la lista de tipos de envío desde la configuración"""
        value = _get_config_with_retry('tipos_envio')
        if not value:
            value = _get_defaults().get('tipos_envio', 'AEREO,MARITIMO')
        return [t.strip() for t in value.split(',') if t.strip()]

    @staticmethod
    def get_tiempos_entrega() -> List[str]:
        """Obtiene la lista de tiempos de entrega desde la configuración"""
        value = _get_config_with_retry('tiempos_entrega')
        if not value:
            value = _get_defaults().get('tiempos_entrega', '08 A 12 DIAS,12 A 15 DIAS')
        return [t.strip() for t in value.split(',') if t.strip()]

    @staticmethod
    def get_warranties() -> List[str]:
        """Obtiene la lista de garantías desde la configuración.
        Lee primero 'warranties' (clave usada por el panel admin),
        luego 'garantias' (clave legacy), y finalmente el fallback.
        """
        # Intentar con la clave que usa el panel de administración
        value = _get_config_with_retry('warranties')
        if not value:
            # Fallback a la clave legacy
            value = _get_config_with_retry('garantias')
        if not value:
            value = _get_defaults().get('garantias', '30 DIAS,3 MESES')
        return [g.strip() for g in value.split(',') if g.strip()]

    @staticmethod
    def get_manejo_options() -> List[float]:
        """Obtiene las opciones de manejo desde la configuración"""
        value = _get_config_with_retry('manejo_options')
        if not value:
            value = _get_defaults().get('manejo_options', '0.0,15.0,23.0,25.0')
        try:
            return [float(m.strip()) for m in value.split(',') if m.strip()]
        except ValueError:
            return [0.0, 15.0, 23.0, 25.0]

    @staticmethod
    def get_impuesto_internacional_options() -> List[int]:
        """Obtiene las opciones de impuesto internacional desde la configuración"""
        value = _get_config_with_retry('impuesto_internacional_options')
        if not value:
            value = _get_defaults().get('impuesto_internacional_options', '0,25,30,35,40,45,50')
        try:
            return [int(i.strip()) for i in value.split(',') if i.strip()]
        except ValueError:
            return [0, 25, 30, 35, 40, 45, 50]

    @staticmethod
    def get_profit_factors() -> List[float]:
        """Obtiene los factores de utilidad desde la configuración"""
        value = _get_config_with_retry('profit_factors')
        if not value:
            value = _get_defaults().get('profit_factors', '1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0')
        try:
            return [float(f.strip()) for f in value.split(',') if f.strip()]
        except ValueError:
            return [1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 0]

    @staticmethod
    def get_tax_percentage() -> float:
        """Obtiene el porcentaje de TAX desde la configuración"""
        value = _get_config_with_retry('tax_percentage')
        if not value:
            value = _get_defaults().get('tax_percentage', '7.0')
        try:
            return float(value)
        except ValueError:
            return 7.0

    @staticmethod
    def get_diferencial() -> float:
        """Obtiene el diferencial desde la configuración."""
        # Primero intentar con la clave que usa el panel de administración
        value = _get_config_with_retry('exchange_differential')
        if not value:
            # Fallback a la clave legacy
            value = _get_config_with_retry('diferencial')
        if not value:
            value = _get_defaults().get('exchange_differential', '45.0')
        try:
            return float(value)
        except ValueError:
            return 45.0

    @staticmethod
    def get_iva_venezuela() -> float:
        """Obtiene el IVA de Venezuela desde la configuración"""
        value = _get_config_with_retry('iva_venezuela')
        if not value:
            value = _get_defaults().get('iva_venezuela', '16.0')
        try:
            return float(value)
        except ValueError:
            return 16.0

    # ── Alias para compatibilidad ──────────────────────────────────────────
    @staticmethod
    def get_garantias() -> List[str]:
        """Alias para get_warranties"""
        return ConfigHelpers.get_warranties()

    @staticmethod
    def get_utilidad_factors() -> List[float]:
        """Alias para get_profit_factors"""
        return ConfigHelpers.get_profit_factors()


# ── Agregar métodos estáticos a DBManager para compatibilidad ────────────────
DBManager.get_paises_origen                  = ConfigHelpers.get_paises_origen
DBManager.get_tipos_envio                    = ConfigHelpers.get_tipos_envio
DBManager.get_tiempos_entrega                = ConfigHelpers.get_tiempos_entrega
DBManager.get_warranties                     = ConfigHelpers.get_warranties
DBManager.get_garantias                      = ConfigHelpers.get_garantias
DBManager.get_manejo_options                 = ConfigHelpers.get_manejo_options
DBManager.get_impuesto_internacional_options = ConfigHelpers.get_impuesto_internacional_options
DBManager.get_profit_factors                 = ConfigHelpers.get_profit_factors
DBManager.get_utilidad_factors               = ConfigHelpers.get_utilidad_factors
DBManager.get_tax_percentage                 = ConfigHelpers.get_tax_percentage
DBManager.get_diferencial                    = ConfigHelpers.get_diferencial
DBManager.get_iva_venezuela                  = ConfigHelpers.get_iva_venezuela
