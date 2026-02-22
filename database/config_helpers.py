"""
Funciones auxiliares para obtener configuraciones del sistema
LogiPartVE Pro v7.0
"""

from database.db_manager import DBManager
from typing import List

class ConfigHelpers:
    """Clase con métodos estáticos para obtener configuraciones"""
    
    @staticmethod
    def get_paises_origen() -> List[str]:
        """Obtiene la lista de países de origen desde la configuración"""
        try:
            config_value = DBManager.get_config('paises_origen')
            if config_value:
                # Asumiendo que están separados por comas
                return [p.strip() for p in config_value.split(',')]
            else:
                # Valores por defecto
                return ["EEUU", "MIAMI", "ESPAÑA", "MADRID", "DUBAI", "CHINA"]
        except Exception as e:
            print(f"Error al obtener países de origen: {e}")
            return ["EEUU", "MIAMI", "ESPAÑA", "MADRID", "DUBAI", "CHINA"]
    
    @staticmethod
    def get_tipos_envio() -> List[str]:
        """Obtiene la lista de tipos de envío desde la configuración"""
        try:
            config_value = DBManager.get_config('tipos_envio')
            if config_value:
                return [t.strip() for t in config_value.split(',')]
            else:
                return ["AEREO", "MARITIMO", "TERRESTRE"]
        except Exception as e:
            print(f"Error al obtener tipos de envío: {e}")
            return ["AEREO", "MARITIMO", "TERRESTRE"]
    
    @staticmethod
    def get_tiempos_entrega() -> List[str]:
        """Obtiene la lista de tiempos de entrega desde la configuración"""
        try:
            config_value = DBManager.get_config('tiempos_entrega')
            if config_value:
                return [t.strip() for t in config_value.split(',')]
            else:
                return ["02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS", "15 A 20 DIAS"]
        except Exception as e:
            print(f"Error al obtener tiempos de entrega: {e}")
            return ["02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS", "15 A 20 DIAS"]
    
    @staticmethod
    def get_warranties() -> List[str]:
        """Obtiene la lista de garantías desde la configuración"""
        try:
            config_value = DBManager.get_config('garantias')
            if config_value:
                return [g.strip() for g in config_value.split(',')]
            else:
                return ["15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES", "1 AÑO"]
        except Exception as e:
            print(f"Error al obtener garantías: {e}")
            return ["15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES", "1 AÑO"]
    
    @staticmethod
    def get_manejo_options() -> List[float]:
        """Obtiene las opciones de manejo desde la configuración"""
        try:
            config_value = DBManager.get_config('manejo_options')
            if config_value:
                return [float(m.strip()) for m in config_value.split(',')]
            else:
                return [0.0, 15.0, 23.0, 25.0]
        except Exception as e:
            print(f"Error al obtener opciones de manejo: {e}")
            return [0.0, 15.0, 23.0, 25.0]
    
    @staticmethod
    def get_impuesto_internacional_options() -> List[int]:
        """Obtiene las opciones de impuesto internacional desde la configuración"""
        try:
            config_value = DBManager.get_config('impuesto_internacional_options')
            if config_value:
                return [int(i.strip()) for i in config_value.split(',')]
            else:
                return [0, 25, 30, 35, 40, 45, 50]
        except Exception as e:
            print(f"Error al obtener opciones de impuesto internacional: {e}")
            return [0, 25, 30, 35, 40, 45, 50]
    
    @staticmethod
    def get_profit_factors() -> List[float]:
        """Obtiene los factores de utilidad desde la configuración"""
        try:
            config_value = DBManager.get_config('profit_factors')
            if config_value:
                return [float(f.strip()) for f in config_value.split(',')]
            else:
                return [1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 0]
        except Exception as e:
            print(f"Error al obtener factores de utilidad: {e}")
            return [1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 0]
    
    @staticmethod
    def get_tax_percentage() -> float:
        """Obtiene el porcentaje de TAX desde la configuración"""
        try:
            config_value = DBManager.get_config('tax_percentage')
            if config_value:
                return float(config_value)
            else:
                return 7.0
        except Exception as e:
            print(f"Error al obtener porcentaje de TAX: {e}")
            return 7.0
    
    @staticmethod
    def get_diferencial() -> float:
        """Obtiene el diferencial desde la configuración"""
        try:
            config_value = DBManager.get_config('diferencial')
            if config_value:
                return float(config_value)
            else:
                return 45.0
        except Exception as e:
            print(f"Error al obtener diferencial: {e}")
            return 45.0
    
    @staticmethod
    def get_iva_venezuela() -> float:
        """Obtiene el IVA de Venezuela desde la configuración"""
        try:
            config_value = DBManager.get_config('iva_venezuela')
            if config_value:
                return float(config_value)
            else:
                return 16.0
        except Exception as e:
            print(f"Error al obtener IVA Venezuela: {e}")
            return 16.0


# Agregar métodos estáticos a DBManager para compatibilidad
DBManager.get_paises_origen = ConfigHelpers.get_paises_origen
DBManager.get_tipos_envio = ConfigHelpers.get_tipos_envio
DBManager.get_tiempos_entrega = ConfigHelpers.get_tiempos_entrega
DBManager.get_warranties = ConfigHelpers.get_warranties
DBManager.get_manejo_options = ConfigHelpers.get_manejo_options
DBManager.get_impuesto_internacional_options = ConfigHelpers.get_impuesto_internacional_options
DBManager.get_profit_factors = ConfigHelpers.get_profit_factors
DBManager.get_tax_percentage = ConfigHelpers.get_tax_percentage
DBManager.get_diferencial = ConfigHelpers.get_diferencial
DBManager.get_iva_venezuela = ConfigHelpers.get_iva_venezuela
