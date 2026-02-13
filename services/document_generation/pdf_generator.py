# services/document_generation/pdf_generator.py
"""
Generador de PDF para cotizaciones de LogiPartVE Pro
Diseño profesional y responsive
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

class PDFQuoteGenerator:
    """Generador de cotizaciones en formato PDF"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configurar estilos personalizados"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Encabezado de sección
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
    
    def generate_quote_pdf(self, quote_data, output_path):
        """
        Genera un PDF de cotización
        
        Args:
            quote_data: Diccionario con datos de la cotización
            output_path: Ruta donde guardar el PDF
        
        Returns:
            str: Ruta del archivo generado o None si hay error
        """
        try:
            # Crear documento
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Contenedor de elementos
            elements = []
            
            # Encabezado
            elements.extend(self._build_header(quote_data))
            
            # Información del cliente
            elements.extend(self._build_client_info(quote_data))
            
            # Tabla de ítems
            elements.extend(self._build_items_table(quote_data))
            
            # Totales
            elements.extend(self._build_totals(quote_data))
            
            # Términos y condiciones
            elements.extend(self._build_terms(quote_data))
            
            # Pie de página
            elements.extend(self._build_footer(quote_data))
            
            # Construir PDF
            doc.build(elements)
            
            return output_path
            
        except Exception as e:
            print(f"Error generando PDF: {e}")
            return None
    
    def _build_header(self, quote_data):
        """Construir encabezado del PDF"""
        elements = []
        
        # Título
        title = Paragraph("LogiPartVE Pro", self.styles['CustomTitle'])
        elements.append(title)
        
        # Subtítulo
        subtitle = Paragraph("Cotización de Repuestos Automotrices", self.styles['CustomSubtitle'])
        elements.append(subtitle)
        
        # Información de cotización
        quote_info_data = [
            ['Cotización N°:', quote_data.get('quote_number', 'N/A')],
            ['Fecha:', datetime.now().strftime('%d/%m/%Y')],
            ['Analista:', quote_data.get('analyst_name', 'N/A')]
        ]
        
        quote_info_table = Table(quote_info_data, colWidths=[2*inch, 4*inch])
        quote_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f77b4')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(quote_info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_client_info(self, quote_data):
        """Construir información del cliente"""
        elements = []
        
        # Encabezado de sección
        section_header = Paragraph("Datos del Cliente", self.styles['SectionHeader'])
        elements.append(section_header)
        
        client_data = quote_data.get('client', {})
        
        client_info_data = [
            ['Cliente:', client_data.get('nombre', 'N/A')],
            ['Teléfono:', client_data.get('telefono', 'N/A')],
            ['Email:', client_data.get('email', 'N/A') if client_data.get('email') else 'No proporcionado'],
            ['Vehículo:', client_data.get('vehiculo', 'N/A')],
            ['Motor:', client_data.get('motor', 'N/A')],
            ['Año:', client_data.get('año', 'N/A')]
        ]
        
        client_table = Table(client_info_data, colWidths=[1.5*inch, 4.5*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(client_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_items_table(self, quote_data):
        """Construir tabla de ítems"""
        elements = []
        
        # Encabezado de sección
        section_header = Paragraph("Detalle de Repuestos", self.styles['SectionHeader'])
        elements.append(section_header)
        
        # Encabezados de tabla
        table_data = [
            ['#', 'Descripción', 'N° Parte', 'Marca', 'Cant.', 'Precio USD']
        ]
        
        # Agregar ítems
        items = quote_data.get('items', [])
        for i, item in enumerate(items, 1):
            table_data.append([
                str(i),
                item.get('descripcion', 'N/A'),
                item.get('parte', 'N/A'),
                item.get('marca', 'N/A'),
                str(item.get('cantidad', 1)),
                f"${item.get('costo_total', 0):.2f}"
            ])
        
        # Crear tabla
        items_table = Table(table_data, colWidths=[0.4*inch, 2.2*inch, 1.2*inch, 1.2*inch, 0.6*inch, 1*inch])
        items_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Cuerpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Columna #
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Columna Cant.
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),   # Columna Precio
            
            # Bordes y líneas
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_totals(self, quote_data):
        """Construir sección de totales"""
        elements = []
        
        total_usd = quote_data.get('total_usd', 0)
        total_bs = quote_data.get('total_bs', 0)
        
        totals_data = [
            ['TOTAL USD:', f"${total_usd:.2f}"],
            ['TOTAL Bs:', f"Bs {total_bs:.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f77b4')),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#1f77b4')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_terms(self, quote_data):
        """Construir términos y condiciones"""
        elements = []
        
        terms_text = quote_data.get('terms', 'Términos y condiciones estándar.')
        
        terms_header = Paragraph("Términos y Condiciones", self.styles['SectionHeader'])
        elements.append(terms_header)
        
        terms_paragraph = Paragraph(terms_text, self.styles['Normal'])
        elements.append(terms_paragraph)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_footer(self, quote_data):
        """Construir pie de página"""
        elements = []
        
        footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )
        
        footer_text = f"LogiPartVE Pro © {datetime.now().year} - Todos los derechos reservados"
        footer = Paragraph(footer_text, footer_style)
        elements.append(footer)
        
        return elements
