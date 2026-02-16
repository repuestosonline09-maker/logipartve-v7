# services/document_generation/pdf_generator.py
"""
Generador de PDF para cotizaciones de JDAE Auto Partes, C.A.
Diseño profesional con branding completo en formato horizontal
"""

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

class PDFQuoteGenerator:
    """Generador de cotizaciones en formato PDF"""
    
    # Colores corporativos
    COLOR_PRIMARY = colors.HexColor('#3b7fc4')  # Azul Auto Online Pro
    COLOR_DARK = colors.HexColor('#1e3a5f')     # Azul oscuro JDAE
    COLOR_GREEN = colors.HexColor('#4a7c59')    # Verde JDAE
    COLOR_TEXT = colors.HexColor('#333333')     # Gris oscuro
    COLOR_LIGHT_BG = colors.HexColor('#f5f5f5') # Gris claro
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        # Determinar ruta base del proyecto
        self.base_path = self._get_base_path()
    
    def _get_base_path(self):
        """Obtener ruta base del proyecto"""
        # Intentar diferentes rutas posibles
        possible_paths = [
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),  # Relativa al archivo
            '/app',  # Railway
            '/tmp/logipartve-v7',  # Desarrollo local
            os.getcwd()  # Directorio actual
        ]
        
        for path in possible_paths:
            logo_path = os.path.join(path, 'assets', 'logos', 'LOGOJDAEAUTOPARTES.png')
            if os.path.exists(logo_path):
                return path
        
        # Si no se encuentra, usar la primera opción
        return possible_paths[0]
    
    def _setup_custom_styles(self):
        """Configurar estilos personalizados"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=self.COLOR_DARK,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # RIF y datos de contacto
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.COLOR_TEXT,
            spaceAfter=3,
            alignment=TA_CENTER
        ))
        
        # Subtítulo de cotización
        self.styles.add(ParagraphStyle(
            name='QuoteTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Encabezado de sección
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=colors.white,
            spaceAfter=6,
            spaceBefore=6,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        ))
        
        # Texto normal pequeño
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=self.COLOR_TEXT
        ))
    
    def generate_quote_pdf(self, quote_data, output_path):
        """
        Genera un PDF de cotización en formato horizontal
        
        Args:
            quote_data: Diccionario con datos de la cotización
            output_path: Ruta donde guardar el PDF
        
        Returns:
            str: Ruta del archivo generado o None si hay error
        """
        try:
            # Crear documento en formato HORIZONTAL
            doc = SimpleDocTemplate(
                output_path,
                pagesize=landscape(letter),  # HORIZONTAL
                rightMargin=0.4*inch,
                leftMargin=0.4*inch,
                topMargin=0.4*inch,
                bottomMargin=0.4*inch
            )
            
            # Contenedor de elementos
            elements = []
            
            # Encabezado con logos y datos de la empresa
            elements.extend(self._build_header(quote_data))
            
            # Información de la cotización y cliente en dos columnas
            elements.extend(self._build_quote_and_client_info(quote_data))
            
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
            import traceback
            traceback.print_exc()
            return None
    
    def _build_header(self, quote_data):
        """Construir encabezado del PDF con logos y datos de empresa"""
        elements = []
        
        # Crear tabla con 3 columnas: Logo JDAE | Info Central | Logo Auto Online Pro
        header_data = []
        
        # Fila 1: Logos y nombre
        logo_jdae = None
        logo_aop = None
        
        logo_jdae_path = os.path.join(self.base_path, 'assets', 'logos', 'LOGOJDAEAUTOPARTES.png')
        logo_aop_path = os.path.join(self.base_path, 'assets', 'logos', 'LogoAutoOnlinePro.png')
        
        if os.path.exists(logo_jdae_path):
            logo_jdae = Image(logo_jdae_path, width=1.2*inch, height=1.2*inch)
        else:
            logo_jdae = Paragraph("JDAE", self.styles['CompanyName'])
        
        if os.path.exists(logo_aop_path):
            logo_aop = Image(logo_aop_path, width=1*inch, height=1*inch)
        else:
            logo_aop = Paragraph("AOP", self.styles['CompanyName'])
        
        # Información central
        company_info = Paragraph(
            "<b>JDAE AUTO PARTES, C.A.</b><br/>"
            "RIF: J-5072639-5<br/>"
            "Av. Francisco de Miranda cruce con calle Los Laboratorios.<br/>"
            "Centro Empresarial Quorum, piso 3 Ofi. 3J. Los Ruices, Caracas. Venezuela<br/>"
            "Tel: (0424) 135-4148 | @repuestosonlinecaracas | www.autoonlinepro.com",
            self.styles['ContactInfo']
        )
        
        rep_info = Paragraph(
            "<b>REPRESENTANTES EXCLUSIVOS DE:</b><br/>AUTO ONLINE PRO<br/>Orlando, USA",
            self.styles['SmallText']
        )
        
        header_data.append([logo_jdae, company_info, [rep_info, logo_aop]])
        
        header_table = Table(header_data, colWidths=[1.5*inch, 5*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Título de cotización
        quote_title = Paragraph("COTIZACIÓN DE REPUESTOS AUTOMOTRICES", self.styles['QuoteTitle'])
        elements.append(quote_title)
        
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_quote_and_client_info(self, quote_data):
        """Construir información de cotización y cliente en formato compacto"""
        elements = []
        
        client_data = quote_data.get('client', {})
        
        # Información de cotización
        quote_info = f"<b>Cotización N°:</b> {quote_data.get('quote_number', 'N/A')} | " \
                     f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')} | " \
                     f"<b>Analista:</b> {quote_data.get('analyst_name', 'N/A')}"
        
        quote_para = Paragraph(quote_info, self.styles['SmallText'])
        elements.append(quote_para)
        
        elements.append(Spacer(1, 0.08*inch))
        
        # Encabezado de cliente
        section_header_table = Table([['DATOS DEL CLIENTE']], colWidths=[10*inch])
        section_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(section_header_table)
        
        # Datos del cliente en tabla compacta
        client_info_data = [
            ['Cliente:', client_data.get('nombre', ''), 
             'Teléfono:', client_data.get('telefono', ''),
             'Email:', client_data.get('email', '')],
            ['Vehículo:', client_data.get('vehiculo', ''),
             'Año:', client_data.get('año', ''),
             'Motor:', client_data.get('motor', '')],
            ['VIN:', client_data.get('vin', ''),
             'C.I./RIF:', client_data.get('ci_rif', ''),
             'Dirección:', client_data.get('direccion', '')]
        ]
        
        client_table = Table(client_info_data, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 1.5*inch, 0.7*inch, 2*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(client_table)
        elements.append(Spacer(1, 0.12*inch))
        
        return elements
    
    def _build_items_table(self, quote_data):
        """Construir tabla de ítems con TODOS los campos en formato horizontal"""
        elements = []
        
        # Encabezado de sección
        section_header_table = Table([['DETALLE DE REPUESTOS']], colWidths=[10*inch])
        section_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(section_header_table)
        
        # Encabezados de tabla - TODOS los campos
        table_data = [
            ['#', 'Descripción', '# Parte', 'Marca', 'Cant.', 
             'Garantía', 'Envío', 'País Loc.', 'País Fab.', 
             'T. Entrega', 'Precio USD']
        ]
        
        # Agregar ítems
        items = quote_data.get('items', [])
        for i, item in enumerate(items, 1):
            table_data.append([
                str(i),
                item.get('descripcion', ''),
                item.get('parte', ''),
                item.get('marca', ''),
                str(item.get('cantidad', 1)),
                item.get('garantia', ''),
                item.get('envio_tipo', ''),
                item.get('origen', ''),
                item.get('fabricacion', ''),
                item.get('tiempo_entrega', ''),
                f"${item.get('costo_total', 0):.2f}"
            ])
        
        # Crear tabla con columnas bien distribuidas en horizontal
        items_table = Table(table_data, colWidths=[
            0.3*inch,   # #
            2*inch,     # Descripción
            0.9*inch,   # # Parte
            0.8*inch,   # Marca
            0.4*inch,   # Cant.
            0.8*inch,   # Garantía
            0.7*inch,   # Envío
            0.8*inch,   # País Loc.
            0.8*inch,   # País Fab.
            0.8*inch,   # T. Entrega
            0.8*inch    # Precio USD
        ])
        
        items_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Cuerpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Columna #
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Columna Cant.
            ('ALIGN', (10, 1), (10, -1), 'RIGHT'), # Columna Precio
            
            # Bordes y líneas
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.12*inch))
        
        return elements
    
    def _build_totals(self, quote_data):
        """Construir sección de totales"""
        elements = []
        
        total_usd = quote_data.get('total_usd', 0)
        total_bs = quote_data.get('total_bs', 0)
        
        totals_data = [
            ['TOTAL USD:', f"${total_usd:.2f}"],
            ['TOTAL Bs:', f"Bs {total_bs:,.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[9*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_PRIMARY),
            ('LINEABOVE', (0, 0), (-1, 0), 1.5, self.COLOR_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_terms(self, quote_data):
        """Construir términos y condiciones"""
        elements = []
        
        terms_text = quote_data.get('terms', 'Términos y condiciones estándar.')
        
        # Encabezado de sección
        section_header_table = Table([['TÉRMINOS Y CONDICIONES']], colWidths=[10*inch])
        section_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(section_header_table)
        
        terms_paragraph = Paragraph(terms_text, self.styles['SmallText'])
        elements.append(terms_paragraph)
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_footer(self, quote_data):
        """Construir pie de página con logo de LogiPartVE"""
        elements = []
        
        # Línea divisoria
        line_table = Table([['']],  colWidths=[10*inch])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
        ]))
        elements.append(line_table)
        
        # Logo pequeño de LogiPartVE y texto en una línea
        logo_lp_path = os.path.join(self.base_path, 'assets', 'logos', 'LOGOLogiPartVE.png')
        
        footer_content = []
        if os.path.exists(logo_lp_path):
            logo_lp = Image(logo_lp_path, width=0.3*inch, height=0.3*inch)
            footer_content.append(logo_lp)
        
        footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        footer_text = Paragraph(
            f"Cotización generada por LogiPartVE.com | © {datetime.now().year} JDAE Auto Partes, C.A. - Todos los derechos reservados",
            footer_style
        )
        
        if footer_content:
            footer_table = Table([[footer_content[0], footer_text]], colWidths=[0.4*inch, 9.6*inch])
            footer_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(footer_table)
        else:
            elements.append(footer_text)
        
        return elements
