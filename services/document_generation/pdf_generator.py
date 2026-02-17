"""
Generador de PDF para Cotizaciones - Diseño International Freight
Estilo: Documento de carga aérea internacional
"""

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import os
from pathlib import Path


def find_logo_path(logo_filename):
    """
    Busca el logo en diferentes ubicaciones posibles
    """
    possible_paths = [
        # Ruta relativa al archivo actual
        Path(__file__).parent.parent.parent / "assets" / "logos" / logo_filename,
        # Ruta desde /app (Railway)
        Path("/app/assets/logos") / logo_filename,
        # Ruta desde /tmp (desarrollo)
        Path("/tmp/logipartve-v7/assets/logos") / logo_filename,
        # Ruta actual
        Path.cwd() / "assets" / "logos" / logo_filename,
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    return None


class InternationalFreightBackground:
    """Clase para dibujar el fondo con marca de agua"""
    
    def __init__(self):
        pass
    
    def draw_watermark(self, canvas_obj, doc):
        """Dibuja la marca de agua con mapa mundial y rutas aéreas"""
        canvas_obj.saveState()
        
        # Configurar transparencia
        canvas_obj.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.15)
        canvas_obj.setStrokeColorRGB(0.85, 0.85, 0.85, alpha=0.2)
        canvas_obj.setLineWidth(0.5)
        
        # Dibujar líneas de coordenadas geográficas (latitud/longitud)
        width = doc.pagesize[0]
        height = doc.pagesize[1]
        
        # Líneas horizontales (latitudes)
        for i in range(5, int(height), 40):
            canvas_obj.line(50, i, width - 50, i)
        
        # Líneas verticales (longitudes)
        for i in range(100, int(width), 60):
            canvas_obj.line(i, 50, i, height - 50)
        
        # Dibujar rutas aéreas (líneas curvas simulando vuelos)
        canvas_obj.setStrokeColorRGB(0.17, 0.49, 0.62, alpha=0.1)
        canvas_obj.setLineWidth(1.5)
        
        # Ruta 1: USA → Venezuela
        canvas_obj.bezier(150, height - 150, 300, height - 100, 500, height - 120, 650, height - 180)
        
        # Ruta 2: Europa → Venezuela
        canvas_obj.bezier(width - 200, height - 120, width - 350, height - 80, width - 500, height - 150, width - 650, height - 200)
        
        # Puntos de origen/destino
        canvas_obj.setFillColorRGB(0.17, 0.49, 0.62, alpha=0.15)
        canvas_obj.circle(150, height - 150, 8, fill=1)  # Origen USA
        canvas_obj.circle(650, height - 180, 8, fill=1)  # Destino Venezuela
        
        # Texto muy sutil "INTERNATIONAL FREIGHT"
        canvas_obj.setFont("Helvetica-Bold", 60)
        canvas_obj.setFillColorRGB(0.95, 0.95, 0.95, alpha=0.08)
        canvas_obj.saveState()
        canvas_obj.translate(width / 2, height / 2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, "INTERNATIONAL")
        canvas_obj.drawCentredString(0, -70, "FREIGHT")
        canvas_obj.restoreState()
        
        canvas_obj.restoreState()


def generar_pdf_cotizacion(datos_cotizacion, output_path):
    """
    Genera un PDF con el diseño International Freight
    
    Args:
        datos_cotizacion: Diccionario con los datos de la cotización
        output_path: Ruta donde se guardará el PDF
    """
    
    # Configuración del documento (horizontal)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Colores del tema
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_NARANJA = colors.HexColor('#FF6B35')
    COLOR_GRIS = colors.HexColor('#2C3E50')
    COLOR_GRIS_CLARO = colors.HexColor('#E8E8E8')
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    style_titulo = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_AZUL_AVIACION,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    style_subtitulo = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_AZUL_AVIACION,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto normal
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        alignment=TA_LEFT
    )
    
    # Estilo para encabezados de sección
    style_seccion = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=COLOR_AZUL_AVIACION,
        spaceAfter=6,
        spaceBefore=8,
        fontName='Helvetica-Bold',
        leftIndent=10
    )
    
    # Contenido del PDF
    story = []
    
    # ==========================================
    # ENCABEZADO CON LOGOS
    # ==========================================
    
    # Buscar logos
    logo_jdae_path = find_logo_path("LOGOJDAEAUTOPARTES.png")
    logo_aop_path = find_logo_path("LogoAutoOnlinePro.png")
    logo_logipart_path = find_logo_path("LOGOLogiPartVE.png")
    
    # Crear tabla para encabezado con logos
    encabezado_data = []
    
    # Fila 1: Logos y título
    fila_logos = []
    
    # Logo JDAE (izquierda)
    if logo_jdae_path:
        img_jdae = Image(logo_jdae_path, width=1.2*inch, height=1.2*inch)
        fila_logos.append(img_jdae)
    else:
        fila_logos.append(Paragraph("<b>JDAE<br/>AUTO PARTES</b>", style_normal))
    
    # Título central
    titulo_central = Paragraph(
        "✈ <b>COTIZACIÓN INTERNACIONAL DE REPUESTOS</b> ✈<br/>"
        "<font size=8>INTERNATIONAL AUTO PARTS QUOTATION</font>",
        style_titulo
    )
    fila_logos.append(titulo_central)
    
    # Logo Auto Online Pro (derecha)
    if logo_aop_path:
        img_aop = Image(logo_aop_path, width=1.2*inch, height=1.2*inch)
        fila_logos.append(img_aop)
    else:
        fila_logos.append(Paragraph("<b>AUTO<br/>ONLINE<br/>PRO USA</b>", style_normal))
    
    encabezado_data.append(fila_logos)
    
    # Fila 2: RIF, subtítulo, representantes
    fila_info = [
        Paragraph("<b>RIF:</b> J-5072639-5", style_normal),
        Paragraph("<b>REPRESENTANTES EXCLUSIVOS</b><br/><font size=7>EXCLUSIVE REPRESENTATIVES</font>", style_subtitulo),
        Paragraph("", style_normal)
    ]
    encabezado_data.append(fila_info)
    
    tabla_encabezado = Table(encabezado_data, colWidths=[2*inch, 5.5*inch, 2*inch])
    tabla_encabezado.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(tabla_encabezado)
    story.append(Spacer(1, 0.1*inch))
    
    # ==========================================
    # INFORMACIÓN DEL DOCUMENTO
    # ==========================================
    
    presupuesto = datos_cotizacion.get('numero_cotizacion', 'N/A')
    fecha = datos_cotizacion.get('fecha', 'N/A')
    
    info_doc_data = [[
        Paragraph(f"<b>DOCUMENTO / DOCUMENT:</b> {presupuesto}", style_normal),
        Paragraph(f"<b>FECHA / DATE:</b> {fecha}", style_normal),
        Paragraph(f"<b>ORIGEN / ORIGIN:</b> EEUU", style_normal),
    ], [
        Paragraph(f"<b>RIF:</b> J-5072639-5", style_normal),
        Paragraph(f"<b>DESTINO / DESTINATION:</b> VENEZUELA", style_normal),
        Paragraph(f"<b>STATUS:</b> COTIZADO / QUOTED", style_normal),
    ]]
    
    tabla_info_doc = Table(info_doc_data, colWidths=[3.16*inch, 3.16*inch, 3.16*inch])
    tabla_info_doc.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, COLOR_AZUL_AVIACION),
        ('INNERGRID', (0, 0), (-1, -1), 1, COLOR_GRIS_CLARO),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS_CLARO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(tabla_info_doc)
    story.append(Spacer(1, 0.15*inch))
    
    # ==========================================
    # DATOS DEL CLIENTE (CONSIGNEE)
    # ==========================================
    
    story.append(Paragraph("▼ CONSIGNEE (DESTINATARIO)", style_seccion))
    
    cliente = datos_cotizacion.get('cliente', {})
    
    cliente_data = [[
        Paragraph(f"<b>Nombre / Name:</b> {cliente.get('nombre', '')}", style_normal),
        Paragraph(f"<b>Teléfono / Phone:</b> {cliente.get('telefono', '')}", style_normal),
        Paragraph(f"<b>Email:</b> {cliente.get('email', '')}", style_normal),
    ], [
        Paragraph(f"<b>Vehículo / Vehicle:</b> {cliente.get('vehiculo', '')}", style_normal),
        Paragraph(f"<b>Año / Year:</b> {cliente.get('año', '')}", style_normal),
        Paragraph(f"<b>VIN:</b> {cliente.get('vin', '')}", style_normal),
    ]]
    
    tabla_cliente = Table(cliente_data, colWidths=[3.16*inch, 3.16*inch, 3.16*inch])
    tabla_cliente.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_CLARO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(tabla_cliente)
    story.append(Spacer(1, 0.15*inch))
    
    # ==========================================
    # DETALLE DE REPUESTOS (CARGO DETAILS)
    # ==========================================
    
    story.append(Paragraph("▼ CARGO DETAILS (DETALLE DE CARGA)", style_seccion))
    
    # Encabezados de tabla
    items_data = [[
        Paragraph("<b>ITEM</b>", style_normal),
        Paragraph("<b>PART #</b>", style_normal),
        Paragraph("<b>BRAND</b>", style_normal),
        Paragraph("<b>WARR.</b>", style_normal),
        Paragraph("<b>QTY</b>", style_normal),
        Paragraph("<b>SHIP</b>", style_normal),
        Paragraph("<b>ORIGIN</b>", style_normal),
        Paragraph("<b>MANUF.</b>", style_normal),
        Paragraph("<b>DELIV.</b>", style_normal),
        Paragraph("<b>VALUE<br/>USD</b>", style_normal),
    ]]
    
    # Agregar ítems
    items = datos_cotizacion.get('items', [])
    for idx, item in enumerate(items, 1):
        # Calcular precio unitario
        cantidad = item.get('cantidad', 1)
        precio_total = item.get('precio_bs', 0)
        precio_unitario = precio_total / cantidad if cantidad > 0 else 0
        
        items_data.append([
            Paragraph(str(idx), style_normal),
            Paragraph(str(item.get('parte', '')), style_normal),
            Paragraph(str(item.get('marca', '')), style_normal),
            Paragraph(str(item.get('garantia', '')), style_normal),
            Paragraph(str(item.get('cantidad', '')), style_normal),
            Paragraph(str(item.get('envio_tipo', '')), style_normal),
            Paragraph(str(item.get('origen', '')), style_normal),
            Paragraph(str(item.get('fabricacion', '')), style_normal),
            Paragraph(str(item.get('tiempo_entrega', '')), style_normal),
            Paragraph(f"${precio_unitario:.2f}", style_normal),
        ])
    
    # Anchos de columna optimizados para horizontal
    col_widths = [0.4*inch, 0.9*inch, 0.8*inch, 0.7*inch, 0.4*inch, 0.7*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.8*inch]
    
    tabla_items = Table(items_data, colWidths=col_widths)
    tabla_items.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_AZUL_AVIACION),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ITEM centrado
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # QTY centrado
        ('ALIGN', (9, 1), (9, -1), 'RIGHT'),   # VALUE alineado a derecha
        
        # Bordes y fondos
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_CLARO),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        
        # Alineación vertical
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(tabla_items)
    story.append(Spacer(1, 0.15*inch))
    
    # ==========================================
    # RESUMEN FINANCIERO (FINANCIAL SUMMARY)
    # ==========================================
    
    story.append(Paragraph("▼ FINANCIAL SUMMARY (RESUMEN FINANCIERO)", style_seccion))
    
    # Calcular totales
    sub_total = datos_cotizacion.get('sub_total', 0)
    iva = datos_cotizacion.get('iva_total', 0)
    total = datos_cotizacion.get('total_a_pagar', 0)
    abona_ya = datos_cotizacion.get('abona_ya', 0)
    en_entrega = datos_cotizacion.get('y_en_entrega', 0)
    
    # Crear tabla de resumen (alineada a la derecha)
    resumen_data = [
        ['', Paragraph("<b>SUBTOTAL ..................</b>", style_normal), Paragraph(f"<b>${sub_total:.2f}</b>", style_normal)],
        ['', Paragraph("<b>VAT 16% ..................</b>", style_normal), Paragraph(f"<b>${iva:.2f}</b>", style_normal)],
        ['', Paragraph("<b>═══════════════════</b>", style_normal), Paragraph("<b>═══════════</b>", style_normal)],
        ['', Paragraph("<b>TOTAL AMOUNT ..........</b>", style_normal), Paragraph(f"<b>${total:.2f}</b>", style_normal)],
        ['', Paragraph("<b>ADVANCE PAYMENT ......</b>", style_normal), Paragraph(f"<b>${abona_ya:.2f}</b>", style_normal)],
        ['', Paragraph("<b>BALANCE ..............</b>", style_normal), Paragraph(f"<b>${en_entrega:.2f}</b>", style_normal)],
    ]
    
    tabla_resumen = Table(resumen_data, colWidths=[4.5*inch, 2.5*inch, 1.5*inch])
    tabla_resumen.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (1, 0), (2, -1), 1.5, COLOR_AZUL_AVIACION),
        ('BACKGROUND', (1, 3), (2, 3), COLOR_GRIS_CLARO),  # Total destacado
    ]))
    
    story.append(tabla_resumen)
    story.append(Spacer(1, 0.15*inch))
    
    # ==========================================
    # TÉRMINOS Y CONDICIONES
    # ==========================================
    
    story.append(Paragraph("▼ TERMS & CONDITIONS (TÉRMINOS Y CONDICIONES)", style_seccion))
    
    terminos = datos_cotizacion.get('terminos_condiciones', 'No especificados')
    
    terminos_data = [[Paragraph(terminos, style_normal)]]
    tabla_terminos = Table(terminos_data, colWidths=[9.5*inch])
    tabla_terminos.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, COLOR_GRIS),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(tabla_terminos)
    story.append(Spacer(1, 0.1*inch))
    
    # ==========================================
    # PIE DE PÁGINA
    # ==========================================
    
    pie_data = [[
        Paragraph("Generated by <b>LogiPartVE.com</b>", style_normal),
        Paragraph("<b>www.autoonlinepro.com</b>", style_normal),
        Paragraph("<b>@repuestosonlinecaracas</b>", style_normal),
    ]]
    
    if logo_logipart_path:
        img_logipart = Image(logo_logipart_path, width=0.4*inch, height=0.4*inch)
        pie_data[0].insert(0, img_logipart)
        col_widths_pie = [0.5*inch, 3*inch, 3*inch, 3*inch]
    else:
        col_widths_pie = [3.16*inch, 3.16*inch, 3.16*inch]
    
    tabla_pie = Table(pie_data, colWidths=col_widths_pie)
    tabla_pie.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_GRIS),
    ]))
    
    story.append(tabla_pie)
    
    # ==========================================
    # GENERAR PDF
    # ==========================================
    
    # Crear instancia de la clase de fondo
    background = InternationalFreightBackground()
    
    # Construir el PDF con la marca de agua
    doc.build(story, onFirstPage=background.draw_watermark, onLaterPages=background.draw_watermark)
    
    return output_path



# ==========================================
# CLASE WRAPPER PARA COMPATIBILIDAD
# ==========================================

class PDFQuoteGenerator:
    """
    Clase wrapper para mantener compatibilidad con el código existente
    """
    
    @staticmethod
    def generate(datos_cotizacion, output_path):
        """
        Genera un PDF de cotización
        
        Args:
            datos_cotizacion: Diccionario con los datos de la cotización
            output_path: Ruta donde se guardará el PDF
            
        Returns:
            str: Ruta del archivo PDF generado
        """
        return generar_pdf_cotizacion(datos_cotizacion, output_path)
