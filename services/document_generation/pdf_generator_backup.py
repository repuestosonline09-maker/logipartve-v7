# services/document_generation/pdf_generator.py
"""
Generador de PDF para cotizaciones de JDAE Auto Partes, C.A.
Diseño profesional horizontal siguiendo formato de ejemplo
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
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=self.COLOR_DARK,
            spaceAfter=2,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=self.COLOR_TEXT,
            spaceAfter=2,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='QuoteNumber',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.red,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=self.COLOR_TEXT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallBold',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=self.COLOR_TEXT,
            fontName='Helvetica-Bold'
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
                pagesize=landscape(letter),
                rightMargin=0.3*inch,
                leftMargin=0.3*inch,
                topMargin=0.3*inch,
                bottomMargin=0.3*inch
            )
            
            # Contenedor de elementos
            elements = []
            
            # Encabezado con logos
            elements.extend(self._build_header(quote_data))
            
            # Información del cliente y vehículo
            elements.extend(self._build_client_info(quote_data))
            
            # Tabla de ítems
            elements.extend(self._build_items_table(quote_data))
            
            # Términos y totales en dos columnas
            elements.extend(self._build_terms_and_totals(quote_data))
            
            # Construir PDF
            doc.build(elements)
            
            return output_path
            
        except Exception as e:
            print(f"Error generando PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_header(self, quote_data):
        """Construir encabezado con logos y datos de empresa"""
        elements = []
        
        # Tabla con 3 columnas: Logo JDAE | Info Central | Logo Auto Online Pro
        logo_jdae_path = os.path.join(self.base_path, 'assets', 'logos', 'LOGOJDAEAUTOPARTES.png')
        logo_aop_path = os.path.join(self.base_path, 'assets', 'logos', 'LogoAutoOnlinePro.png')
        
        # Logo JDAE
        if os.path.exists(logo_jdae_path):
            logo_jdae = Image(logo_jdae_path, width=1*inch, height=1*inch)
        else:
            logo_jdae = Paragraph("JDAE", self.styles['CompanyName'])
        
        # Información central
        central_info = []
        central_info.append(Paragraph("<b>DIRECCIÓN ÚNICA:</b>", self.styles['SmallBold']))
        central_info.append(Paragraph(
            "Av. Francisco de Miranda, cruce con calle los Laboratorios<br/>"
            "Centro Empresarial Quorum, piso 3 Oficina 3J. Los Ruices, Caracas. Venezuela",
            self.styles['ContactInfo']
        ))
        central_info.append(Spacer(1, 0.05*inch))
        central_info.append(Paragraph("@repuestosonlinecaracas", self.styles['ContactInfo']))
        central_info.append(Paragraph("0424-135-4148", self.styles['ContactInfo']))
        central_info.append(Spacer(1, 0.05*inch))
        central_info.append(Paragraph("<b>WWW.AUTOONLINEPRO.COM</b>", self.styles['SmallBold']))
        
        # Logo Auto Online Pro con texto
        if os.path.exists(logo_aop_path):
            logo_aop = Image(logo_aop_path, width=0.9*inch, height=0.9*inch)
        else:
            logo_aop = Paragraph("AOP", self.styles['CompanyName'])
        
        rep_text = Paragraph(
            "<b>REPRESENTANTES<br/>EXCLUSIVOS</b>",
            self.styles['SmallBold']
        )
        
        header_data = [[logo_jdae, central_info, [rep_text, logo_aop]]]
        
        header_table = Table(header_data, colWidths=[1.2*inch, 5.5*inch, 1.3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        
        # RIF y número de cotización
        rif_quote_data = [
            [Paragraph("RIF: J-5072639-5", self.styles['SmallText']),
             Paragraph(f"<b>Presupuesto: <font color='red'>{quote_data.get('quote_number', 'N/A')}</font></b>", self.styles['SmallBold'])]
        ]
        
        rif_quote_table = Table(rif_quote_data, colWidths=[1.2*inch, 6.8*inch])
        rif_quote_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(rif_quote_table)
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_client_info(self, quote_data):
        """Construir información del cliente y vehículo"""
        elements = []
        
        client_data = quote_data.get('client', {})
        
        # Fecha y datos básicos
        info_data = [
            [f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", '', ''],
            [f"A la atención de: {client_data.get('nombre', '')}", 
             f"Asesor de Venta: {quote_data.get('analyst_name', 'N/A')}",
             'ORIGEN    EEUU'],
            [f"Teléfono: {client_data.get('telefono', '')}", '', 'DESTINO VENEZUELA'],
            [f"Vehículo: {client_data.get('vehiculo', '')}  Año: {client_data.get('año', '')}  Nro. VIN: {client_data.get('vin', '')}", 
             '', 
             f"VALIDO HASTA    {(datetime.now()).strftime('%d/%m/%Y')}"]
        ]
        
        info_table = Table(info_data, colWidths=[3.5*inch, 2.5*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.COLOR_TEXT),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.08*inch))
        
        return elements
    
    def _build_items_table(self, quote_data):
        """Construir tabla de ítems"""
        elements = []
        
        # Encabezados
        headers = ['DESCRIPCION', '# PARTE', 'MARCA', 'TIEMPO DE\nGARANTIA', 'CANT.', 
                   'ENVIO', 'PAIS DE\nLOCALIZACION', 'PAIS DE\nFABRICACION', 
                   'TIEMPO DE\nENTREGA', 'COSTO UNIT.', 'COSTO TOTAL']
        
        table_data = [headers]
        
        # Agregar ítems
        items = quote_data.get('items', [])
        for item in items:
            # Calcular precio unitario y total (con diferencial, sin IVA)
            precio_unit = item.get('precio_usd', 0) + item.get('diferencial_valor', 0)
            precio_total = precio_unit * item.get('cantidad', 1)
            
            table_data.append([
                item.get('descripcion', ''),
                item.get('parte', ''),
                item.get('marca', ''),
                item.get('garantia', ''),
                str(item.get('cantidad', 1)),
                item.get('envio_tipo', ''),
                item.get('origen', ''),
                item.get('fabricacion', ''),
                item.get('tiempo_entrega', ''),
                f"${precio_unit:.2f}",
                f"${precio_total:.2f}"
            ])
        
        # Agregar filas vacías si hay menos de 8 ítems
        while len(table_data) < 9:  # 1 header + 8 filas
            table_data.append(['', '', '', '', '0', '', '', '', '', '#¡DIV/0!', '$0.00'])
        
        items_table = Table(table_data, colWidths=[
            1.5*inch,   # Descripción
            0.7*inch,   # # Parte
            0.7*inch,   # Marca
            0.6*inch,   # Garantía
            0.35*inch,  # Cant.
            0.6*inch,   # Envío
            0.7*inch,   # País Loc.
            0.7*inch,   # País Fab.
            0.7*inch,   # Tiempo Entrega
            0.7*inch,   # Costo Unit.
            0.7*inch    # Costo Total
        ])
        
        items_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_LIGHT_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLOR_TEXT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Cuerpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Cant.
            ('ALIGN', (9, 1), (10, -1), 'RIGHT'),  # Costos
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.08*inch))
        
        return elements
    
    def _build_terms_and_totals(self, quote_data):
        """Construir términos y totales en dos columnas"""
        elements = []
        
        # Calcular totales
        items = quote_data.get('items', [])
        
        # Sub-Total: suma de precios con diferencial, sin IVA
        sub_total = sum(
            (item.get('precio_usd', 0) + item.get('diferencial_valor', 0)) * item.get('cantidad', 1)
            for item in items
        )
        
        # IVA: suma de IVA de cada ítem
        iva_total = sum(
            item.get('iva_valor', 0) * item.get('cantidad', 1)
            for item in items
        )
        
        # Total a Pagar
        total_a_pagar = sub_total + iva_total
        
        # Abona Ya: suma de costos base SIN envío
        abona_ya = sum(
            (item.get('costo_fob', 0) +
             item.get('costo_handling', 0) +
             item.get('costo_manejo', 0) +
             item.get('costo_impuesto', 0) +
             item.get('utilidad_valor', 0) +
             item.get('costo_tax', 0)) * item.get('cantidad', 1)
            for item in items
        )
        
        # Y en la Entrega
        y_en_entrega = total_a_pagar - abona_ya
        
        # Términos y condiciones (columna izquierda)
        terms_text = quote_data.get('terms', 'Términos y condiciones estándar.')
        terms_para = Paragraph(terms_text, self.styles['SmallText'])
        
        # Totales (columna derecha)
        totales_data = [
            ['', 'Sub-Total:', f"${sub_total:.2f}"],
            ['', f'I.V.A. 16%:', f"${iva_total:.2f}"],
            ['', 'Total a\nPagar:', f"${total_a_pagar:.2f}"],
            ['¿Cómo Pagas?', '', ''],
            ['', 'Abona Ya:', f"${abona_ya:.2f}"],
            ['', 'Y en la\nEntrega:', f"${y_en_entrega:.2f}"]
        ]
        
        totales_table = Table(totales_data, colWidths=[0.6*inch, 0.6*inch, 0.6*inch])
        totales_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            # Línea arriba de Total a Pagar
            ('LINEABOVE', (1, 2), (2, 2), 1, colors.black),
            # Fondo gris para "¿Cómo Pagas?"
            ('BACKGROUND', (0, 3), (2, 3), self.COLOR_LIGHT_BG),
            ('SPAN', (0, 3), (2, 3)),
            ('ALIGN', (0, 3), (0, 3), 'CENTER'),
        ]))
        
        # Tabla principal con términos y totales
        main_data = [[terms_para, totales_table]]
        
        main_table = Table(main_data, colWidths=[6.2*inch, 1.8*inch])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        
        elements.append(main_table)
        
        # Pie de página con garantía
        elements.append(Spacer(1, 0.05*inch))
        
        garantia_table = Table([
            [Paragraph(
                "Todos nuestros repuestos cuentan con GARANTIA de Satisfacción Total, Cambio, Reembolso y Asistencia Tecnomecánica de ser necesario.<br/>"
                "(Aplican Condiciones)",
                self.styles['SmallText']
            )]
        ], colWidths=[10*inch])
        garantia_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.COLOR_DARK),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(garantia_table)
        
        return elements
    
    def _calculate_totals(self, items):
        """Calcular todos los totales necesarios"""
        sub_total = 0
        iva_total = 0
        abona_ya = 0
        total_usd_divisas = 0
        
        for item in items:
            cantidad = item.get('cantidad', 1)
            
            # Sub-Total (precio Bs con diferencial, sin IVA)
            precio_bs_sin_iva = item.get('precio_usd', 0) + item.get('diferencial_valor', 0)
            sub_total += precio_bs_sin_iva * cantidad
            
            # IVA
            if item.get('aplicar_iva', False):
                iva_total += item.get('iva_valor', 0) * cantidad
            
            # Abona Ya (costos base SIN envío)
            abona_item = (
                item.get('costo_fob', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_tax', 0)
            ) * cantidad
            abona_ya += abona_item
            
            # Total USD Divisas (costos base CON envío)
            total_usd_item = (
                item.get('costo_fob', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_envio', 0) +
                item.get('costo_tax', 0)
            ) * cantidad
            total_usd_divisas += total_usd_item
        
        # Total a Pagar
        total_a_pagar = sub_total + iva_total
        
        # Y en la Entrega
        y_en_entrega = total_a_pagar - abona_ya
        
        return {
            'sub_total': sub_total,
            'iva_total': iva_total,
            'total_a_pagar': total_a_pagar,
            'abona_ya': abona_ya,
            'y_en_entrega': y_en_entrega,
            'total_usd_divisas': total_usd_divisas
        }
