# services/document_generation/png_generator.py
"""
Generador de PNG para cotizaciones de LogiPartVE Pro
Convierte PDF a PNG de alta calidad
"""

from pdf2image import convert_from_path
import os

class PNGQuoteGenerator:
    """Generador de cotizaciones en formato PNG"""
    
    def __init__(self):
        self.dpi = 300  # Alta calidad para WhatsApp/Instagram
    
    def generate_quote_png(self, pdf_path, output_path):
        """
        Genera un PNG de alta calidad desde un PDF
        
        Args:
            pdf_path: Ruta del PDF fuente
            output_path: Ruta donde guardar el PNG
        
        Returns:
            str: Ruta del archivo generado o None si hay error
        """
        try:
            # Convertir PDF a imágenes
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='png'
            )
            
            if images:
                # Guardar la primera página (cotización de una página)
                images[0].save(output_path, 'PNG', quality=95, optimize=True)
                return output_path
            else:
                print("No se pudieron generar imágenes del PDF")
                return None
                
        except Exception as e:
            print(f"Error generando PNG: {e}")
            return None
    
    def generate_quote_png_from_data(self, quote_data, output_path):
        """
        Genera un PNG directamente desde los datos de cotización
        (genera PDF temporal y luego lo convierte a PNG)
        
        Args:
            quote_data: Diccionario con datos de la cotización
            output_path: Ruta donde guardar el PNG
        
        Returns:
            str: Ruta del archivo generado o None si hay error
        """
        try:
            from .pdf_generator import PDFQuoteGenerator
            import tempfile
            
            # Crear PDF temporal
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf_path = tmp_pdf.name
            
            # Generar PDF
            pdf_path = PDFQuoteGenerator.generate(quote_data, tmp_pdf_path)
            
            if not pdf_path:
                return None
            
            # Convertir a PNG
            png_path = self.generate_quote_png(pdf_path, output_path)
            
            # Limpiar archivo temporal
            try:
                os.unlink(tmp_pdf_path)
            except:
                pass
            
            return png_path
            
        except Exception as e:
            print(f"Error generando PNG desde datos: {e}")
            return None
