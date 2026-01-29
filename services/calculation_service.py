"""
Servicio de cálculos de flete y peso volumétrico
"""
from database.db_manager import DBManager


class CalculationService:
    """Servicio para cálculos de logística y flete"""
    
    def calculate_volumetric_weight(self, length_cm: float, width_cm: float, 
                                   height_cm: float) -> float:
        """
        Calcula peso volumétrico
        Fórmula: (L × A × H) / 5000
        
        Args:
            length_cm: Largo en centímetros
            width_cm: Ancho en centímetros
            height_cm: Alto en centímetros
        
        Returns:
            float: Peso volumétrico en kg
        """
        return (length_cm * width_cm * height_cm) / 5000
    
    def get_freight_rate(self, origin: str, shipping_type: str) -> dict:
        """
        Obtiene tarifa de flete desde base de datos
        
        Args:
            origin: Puerto de origen (Miami, Madrid, Dubai)
            shipping_type: Tipo de envío (Aéreo, Marítimo)
        
        Returns:
            dict: {
                'rate': float,
                'unit': str,
                'origin': str,
                'shipping_type': str
            }
        """
        rate = DBManager.get_freight_rate(origin, shipping_type)
        
        if not rate:
            return {
                'rate': 0,
                'unit': '',
                'origin': origin,
                'shipping_type': shipping_type,
                'error': 'Tarifa no encontrada'
            }
        
        # Determinar unidad según origen y tipo
        if shipping_type == "Aéreo":
            unit = "$/lb" if origin == "Miami" else "$/kg"
        else:  # Marítimo
            unit = "$/ft³"
        
        return {
            'rate': rate,
            'unit': unit,
            'origin': origin,
            'shipping_type': shipping_type
        }
    
    def calculate_freight_cost(self, origin: str, shipping_type: str,
                              actual_weight_kg: float, volumetric_weight_kg: float,
                              length_cm: float, width_cm: float, height_cm: float) -> dict:
        """
        Calcula costo de flete según origen y tipo de envío
        
        Args:
            origin: Puerto de origen
            shipping_type: Tipo de envío
            actual_weight_kg: Peso real en kg
            volumetric_weight_kg: Peso volumétrico en kg
            length_cm: Largo en cm
            width_cm: Ancho en cm
            height_cm: Alto en cm
        
        Returns:
            dict: {
                'freight_cost': float,
                'weight_used': float,
                'weight_type': str,
                'rate': float,
                'unit': str,
                'calculation_details': str
            }
        """
        rate_info = self.get_freight_rate(origin, shipping_type)
        
        if 'error' in rate_info:
            return {
                'freight_cost': 0,
                'error': rate_info['error']
            }
        
        rate = rate_info['rate']
        unit = rate_info['unit']
        
        # Determinar qué peso usar
        if shipping_type == "Aéreo":
            # Aéreo: usar el mayor entre peso real y volumétrico
            weight_used = max(actual_weight_kg, volumetric_weight_kg)
            weight_type = "Volumétrico" if volumetric_weight_kg > actual_weight_kg else "Real"
            
            if origin == "Miami":
                # Miami Aéreo: $/lb
                weight_lb = weight_used * 2.20462
                freight_cost = weight_lb * rate
                calculation = f"{weight_lb:.2f} lb × ${rate}/lb = ${freight_cost:.2f}"
            else:
                # Madrid Aéreo: $/kg
                freight_cost = weight_used * rate
                calculation = f"{weight_used:.2f} kg × ${rate}/kg = ${freight_cost:.2f}"
        
        else:  # Marítimo
            # Marítimo: usar pies cúbicos
            volume_m3 = (length_cm * width_cm * height_cm) / 1000000
            volume_ft3 = volume_m3 * 35.3147
            freight_cost = volume_ft3 * rate
            weight_used = volume_ft3
            weight_type = "Volumen"
            calculation = f"{volume_ft3:.2f} ft³ × ${rate}/ft³ = ${freight_cost:.2f}"
        
        return {
            'freight_cost': round(freight_cost, 2),
            'weight_used': round(weight_used, 2),
            'weight_type': weight_type,
            'rate': rate,
            'unit': unit,
            'calculation_details': calculation
        }
