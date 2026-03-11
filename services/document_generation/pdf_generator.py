"""
Generador de PDF para Cotizaciones - Diseño International Freight
Estilo: Documento de carga aérea internacional
"""

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import os
from pathlib import Path


def clean_text(value) -> str:
    """
    Elimina caracteres de control y no imprimibles de un valor de texto.
    Esto evita que aparezcan cuadros negros en el PDF/PNG generado.

    Categorias Unicode eliminadas:
    - Cc: Caracteres de control (U+0000-U+001F, U+007F, U+0080-U+009F)
    - Cf: Caracteres de formato invisibles (zero-width space, BOM, etc.)
    - Zs: Espacios Unicode especiales (no-break space U+00A0, em space, en space,
          thin space, hair space, narrow no-break space, etc.) que WhatsApp y
          los contactos del celular insertan al copiar numeros de telefono.
          ReportLab no puede renderizarlos y los muestra como cuadros negros.
    - Zl: Separador de linea (U+2028)
    - Zp: Separador de parrafo (U+2029)

    Los espacios normales ASCII (U+0020) se conservan.
    """
    import unicodedata
    if value is None:
        return ''
    text = str(value)
    # Categorias problematicas para ReportLab
    _BAD_CATEGORIES = {'Cc', 'Cf', 'Zs', 'Zl', 'Zp'}
    cleaned = ''.join(
        ch if ch == ' ' else  # Preservar espacio ASCII normal
        ch for ch in text
        if ch == ' ' or (unicodedata.category(ch) not in _BAD_CATEGORIES and ord(ch) >= 32)
    )
    return cleaned.strip()


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
        rightMargin=0.4*inch,
        leftMargin=0.4*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )
    
    # Colores del tema
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')  # Azul aviación original
    COLOR_AZUL_AOP = colors.HexColor('#2c7ebe')  # Azul del logo AUTO ONLINE PRO
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
    
    # Estilo para encabezados de tabla (centrado)
    style_header = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
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
    # ENCABEZADO CON LOGOS Y DISEÑO COMPLETO
    # ==========================================
    
    # Buscar todos los logos
    logo_jdae_path = find_logo_path("LOGOJDAEAUTOPARTES.png")
    logo_aop_path = find_logo_path("LogoAutoOnlinePro.png")
    logo_fb_path = find_logo_path("LOGOFACEBOOK.png")
    logo_ig_path = find_logo_path("LOGOINSTAGRAM.png")
    logo_tel_path = find_logo_path("LOGOTELEFONO.png")
    logo_wa_path = find_logo_path("LOGOWHATSAPP.png")
    
    # Estilos para el header
    style_header_titulo = ParagraphStyle(
        'HeaderTitulo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_header_empresa = ParagraphStyle(
        'HeaderEmpresa',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_header_direccion = ParagraphStyle(
        'HeaderDireccion',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        alignment=TA_CENTER
    )
    
    style_header_contacto = ParagraphStyle(
        'HeaderContacto',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        alignment=TA_CENTER
    )
    
    style_header_web = ParagraphStyle(
        'HeaderWeb',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_rif_representantes = ParagraphStyle(
        'RifRepresentantes',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Crear bloque central
    bloque_central_data = []
    
    # Línea 1: Título principal
    bloque_central_data.append([Paragraph("✈ <b>COTIZACIÓN INTERNACIONAL DE REPUESTOS</b> ✈", style_header_titulo)])
    
    # Línea 2: Nombre empresa
    bloque_central_data.append([Paragraph("<b>JDAE AUTO PARTS, C.A.</b>", style_header_empresa)])
    
    # Línea 3-4: Dirección (2 líneas)
    bloque_central_data.append([Paragraph("Av. Francisco de Miranda cruce con calle Los Laboratorios,", style_header_direccion)])
    bloque_central_data.append([Paragraph("Centro Empresarial Quorum. Piso 3 ofic 3J. Los Ruices, Caracas.", style_header_direccion)])
    
    # Línea 5: Redes sociales con logos (usando imágenes inline)
    redes_html = '<para alignment="center">'
    if logo_ig_path:
        redes_html += f'<img src="{logo_ig_path}" width="12" height="12" valign="middle"/> '
    if logo_fb_path:
        redes_html += f'<img src="{logo_fb_path}" width="12" height="12" valign="middle"/> '
    redes_html += '@repuestosonlinecaracas</para>'
    bloque_central_data.append([Paragraph(redes_html, style_header_contacto)])
    
    # Línea 6: Contacto con logos (usando imágenes inline)
    contacto_html = '<para alignment="center">'
    if logo_tel_path:
        contacto_html += f'<img src="{logo_tel_path}" width="12" height="12" valign="middle"/> '
    if logo_wa_path:
        contacto_html += f'<img src="{logo_wa_path}" width="12" height="12" valign="middle"/> '
    contacto_html += 'Contáctanos 0424-1354148</para>'
    bloque_central_data.append([Paragraph(contacto_html, style_header_contacto)])
    
    # Línea 7: Website
    bloque_central_data.append([Paragraph("<b>www.autoonlinepro.com</b>", style_header_web)])
    
    tabla_bloque_central = Table(bloque_central_data, colWidths=[3.5*inch])
    tabla_bloque_central.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    # Crear columna izquierda (Logo JDAE + RIF)
    columna_izq_data = []
    if logo_jdae_path:
        columna_izq_data.append([Image(logo_jdae_path, width=1.5*inch, height=1.5*inch)])
    columna_izq_data.append([Paragraph("<b>J-5072639-5</b>", style_rif_representantes)])
    
    tabla_izq = Table(columna_izq_data, colWidths=[1.5*inch])
    tabla_izq.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    # Crear columna derecha (Logo AOP + Representantes)
    columna_der_data = []
    if logo_aop_path:
        columna_der_data.append([Image(logo_aop_path, width=1.2*inch, height=1.2*inch)])
    columna_der_data.append([Paragraph("<b>REPRESENTANTES EXCLUSIVOS<br/>PARA VENEZUELA</b>", style_rif_representantes)])
    
    tabla_der = Table(columna_der_data, colWidths=[1.8*inch])
    tabla_der.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Ensamblar header completo (3 columnas)
    header_completo = Table([[tabla_izq, tabla_bloque_central, tabla_der]], colWidths=[2*inch, 3.5*inch, 2*inch])
    header_completo.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    story.append(header_completo)
    story.append(Spacer(1, 0.02*inch))
    
    # ==========================================
    # INFORMACIÓN DEL DOCUMENTO
    # ==========================================
    
    # Soportar ambos formatos de nombres de campos (compatibilidad)
    presupuesto = datos_cotizacion.get('numero_cotizacion') or datos_cotizacion.get('quote_number', 'N/A')
    fecha_raw = datos_cotizacion.get('fecha', 'N/A')
    
    # Si no hay fecha, intentar obtener la fecha actual en hora de Caracas (UTC-4)
    if fecha_raw == 'N/A':
        try:
            import sys, os as _os
            sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
            from services.timezone_utils import now_caracas_naive
            fecha_raw = now_caracas_naive().strftime('%Y-%m-%d')
        except Exception:
            from datetime import datetime, timezone, timedelta
            fecha_raw = datetime.now(tz=timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')
    
    # Convertir fecha a formato dd/mm/aa
    from datetime import datetime
    try:
        if fecha_raw != 'N/A':
            fecha_obj = datetime.strptime(fecha_raw, '%Y-%m-%d')
            fecha = fecha_obj.strftime('%d/%m/%y')
        else:
            fecha = 'N/A'
    except:
        fecha = fecha_raw
    
    # Obtener nombre del asesor de ventas (usuario que creó la cotización)
    # Soportar ambos formatos: 'asesor_ventas' o 'analyst_name'
    asesor = datos_cotizacion.get('asesor_ventas') or datos_cotizacion.get('analyst_name', 'N/A')
    
    # Crear estilo para texto rojo
    style_rojo = ParagraphStyle(
        'Rojo',
        parent=style_normal,
        textColor=colors.red
    )
    
    info_doc_data = [[
        Paragraph(f"<b><font color='red'>COTIZACIÓN Nº:</font></b> {presupuesto}", style_normal),
        Paragraph(f"<b>FECHA:</b> {fecha}", style_normal),
        Paragraph(f"<b>ASESOR DE VENTAS:</b> {asesor}", style_normal),
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
    # DATOS DEL CLIENTE
    # ==========================================
    
    story.append(Paragraph("▼ DATOS DEL CLIENTE", style_seccion))
    
    # Soportar ambos formatos: 'cliente' o 'client'
    cliente = datos_cotizacion.get('cliente') or datos_cotizacion.get('client', {})
    
    # Combinar vehículo y cilindrada/motor
    # Soportar ambos formatos: 'cilindrada' o 'motor'
    vehiculo_completo = cliente.get('vehiculo', '')
    cilindrada = cliente.get('cilindrada') or cliente.get('motor', '')
    if cilindrada:
        vehiculo_completo = f"{vehiculo_completo} {cilindrada}"
    
    # Limpiar todos los campos del cliente para eliminar caracteres de control
    c_nombre    = clean_text(cliente.get('nombre', ''))
    c_ci_rif    = clean_text(cliente.get('ci_rif', ''))
    c_telefono  = clean_text(cliente.get('telefono', ''))
    c_email     = clean_text(cliente.get('email', ''))
    c_direccion = clean_text(cliente.get('direccion', ''))
    c_vehiculo  = clean_text(vehiculo_completo)
    c_año       = clean_text(cliente.get('año', ''))
    c_vin       = clean_text(cliente.get('vin', ''))

    cliente_data = [[
        Paragraph(f"<b>NOMBRE:</b> {c_nombre}", style_normal),
        Paragraph(f"<b>CÉDULA O RIF:</b> {c_ci_rif}", style_normal),
        Paragraph(f"<b>TELÉFONO:</b> {c_telefono}", style_normal),
    ], [
        Paragraph(f"<b>EMAIL:</b> {c_email}", style_normal),
        Paragraph(f"<b>DIRECCIÓN:</b> {c_direccion}", style_normal),
        Paragraph(f"<b>VEHÍCULO:</b> {c_vehiculo}", style_normal),
    ], [
        Paragraph(f"<b>AÑO:</b> {c_año}", style_normal),
        Paragraph(f"<b>VIN:</b> {c_vin}", style_normal),
        Paragraph("", style_normal),  # Celda vacía
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
    story.append(Spacer(1, 0.08*inch))  # Espacio reducido (antes 0.15)
    
    # ==========================================
    # TABLA DE ITEMS (SIN TÍTULO)
    # ==========================================
    
    # Encabezados de tabla con nuevos nombres (usando texto simple para evitar word wrap)
    items_data = [[
        "ITEM",
        "DESCRIPCION",
        "# PARTE",
        "MARCA",
        "GARANTIA",
        "QTY",
        "ENVIO",
        "ORIGEN",
        "FABRICACION",
        "ENTREGA",
        "UNIT",
        "TOTAL",
    ]]
    
    # Agregar ítems
    items = datos_cotizacion.get('items', [])
    for idx, item in enumerate(items, 1):
        # Calcular precio unitario y total
        cantidad = item.get('cantidad', 1)
        precio_total = item.get('precio_bs', 0)
        precio_unitario = precio_total / cantidad if cantidad > 0 else 0
        
        # Obtener descripción del repuesto
        descripcion = item.get('descripcion', '') or item.get('descripcion_repuesto', '')
        
        items_data.append([
            Paragraph(str(idx), style_normal),
            Paragraph(str(descripcion), style_normal),
            Paragraph(str(item.get('parte', '')), style_normal),
            Paragraph(str(item.get('marca', '')), style_normal),
            Paragraph(str(item.get('garantia', '')), style_normal),
            Paragraph(str(item.get('cantidad', '')), style_normal),
            Paragraph(str(item.get('envio_tipo', '')), style_normal),
            Paragraph(str(item.get('origen', '')), style_normal),
            Paragraph(str(item.get('fabricacion', '')), style_normal),
            Paragraph(str(item.get('tiempo_entrega', '')), style_normal),
            Paragraph(f"${precio_unitario:.2f}", style_normal),
            Paragraph(f"${precio_total:.2f}", style_normal),
        ])
    
    # Anchos de columna optimizados (12 columnas) - Ajustados para alineación perfecta con DATOS DEL CLIENTE (9.48 inches total)
    col_widths = [0.4*inch, 1.7*inch, 0.95*inch, 0.85*inch, 0.6*inch, 0.4*inch, 0.6*inch, 0.7*inch, 0.78*inch, 0.5*inch, 1.0*inch, 1.0*inch]
    
    # ── Compresión calibrada para máximo 5 ítems en UNA SOLA HOJA ──────────────────────
    # El sistema acepta máximo 5 ítems por cotización.
    # La compresión aumenta progresivamente para garantizar que todo quede en una página.
    #
    # Lógica: se calcula un "score de densidad" combinando cantidad de ítems
    # y longitud máxima de texto en las columnas más anchas (descripción y origen).
    # Esto garantiza que ítems con texto largo (ej. 'Emiratos Árabes Unidos') también
    # se compriman correctamente aunque sean pocos ítems.
    num_items = len(items)

    # Calcular longitud máxima de texto en columnas críticas (descripción + origen)
    _max_text_len = 0
    for item in items:
        desc = str(item.get('descripcion', '') or item.get('descripcion_repuesto', ''))
        orig = str(item.get('origen', ''))
        _max_text_len = max(_max_text_len, len(desc), len(orig))

    # Score de densidad: combina ítems y longitud de texto
    # Texto > 15 chars en columnas críticas equivale a +1 ítem de densidad
    _density = num_items + (1 if _max_text_len > 15 else 0) + (1 if _max_text_len > 25 else 0)

    if _density <= 2:          # 1-2 ítems con texto corto
        _font_header  = 6.5
        _font_content = 7.0
        _pad_v        = 5
    elif _density <= 3:        # 3 ítems o texto moderado
        _font_header  = 6.0
        _font_content = 6.5
        _pad_v        = 4
    elif _density <= 4:        # 4 ítems o texto largo
        _font_header  = 5.5
        _font_content = 6.0
        _pad_v        = 2
    else:                      # 5 ítems o texto muy largo (máximo del sistema)
        _font_header  = 5.0
        _font_content = 5.5
        _pad_v        = 1
    # ─────────────────────────────────────────────────────────────────────────────────

    tabla_items = Table(items_data, colWidths=col_widths)
    tabla_items.setStyle(TableStyle([
        # Encabezado con color azul AUTO ONLINE PRO
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_AZUL_AOP),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), _font_header),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), _font_content),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ITEM centrado
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # QTY centrado
        ('ALIGN', (10, 1), (10, -1), 'RIGHT'),  # UNIT alineado a derecha
        ('ALIGN', (11, 1), (11, -1), 'RIGHT'),  # TOTAL alineado a derecha
        
        # Bordes y fondos con color azul AUTO ONLINE PRO
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_AZUL_AOP),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_CLARO),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
        
        # Padding dinámico según cantidad de ítems
        ('TOPPADDING',    (0, 0), (-1, -1), _pad_v),
        ('BOTTOMPADDING', (0, 0), (-1, -1), _pad_v),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        
        # Alineación vertical
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(tabla_items)
    story.append(Spacer(1, 0.12*inch))

    # ── Una sola hoja garantizada ────────────────────────────────────────────────────
    # Con máximo 5 ítems y la compresión calibrada arriba, todo cabe en una página.
    # No se usa KeepTogether ni PageBreak: el PDF siempre es de una sola hoja.
    # ─────────────────────────────────────────────────────────────────────────────
    
    # ==========================================
    # 4TO Y 5TO BLOQUE: TÉRMINOS (IZQ) + FINANCIAL SUMMARY (DER)
    # Layout de 2 columnas en el mismo nivel horizontal
    # ==========================================
    
    # Calcular totales para FINANCIAL SUMMARY
    sub_total = datos_cotizacion.get('sub_total', 0)
    iva = datos_cotizacion.get('iva_total', 0)
    total = datos_cotizacion.get('total_a_pagar', 0)
    abona_ya = datos_cotizacion.get('abona_ya', 0)
    en_entrega = datos_cotizacion.get('y_en_entrega', 0)
    
    # Obtener términos y condiciones desde datos_cotizacion
    terminos_raw = datos_cotizacion.get('terminos_condiciones', 'Términos y condiciones estándar')
    
    # Preservar saltos de línea reemplazando \n con <br/>
    terminos_html = terminos_raw.replace('\n', '<br/>')
    
    # COLUMNA IZQUIERDA: TÉRMINOS Y CONDICIONES
    col_izq_data = [
        [Paragraph("<b>▼ TÉRMINOS Y CONDICIONES</b>", style_seccion)],
        [Paragraph(terminos_html, style_normal)]
    ]
    
    tabla_col_izq = Table(col_izq_data, colWidths=[3.8*inch])
    tabla_col_izq.setStyle(TableStyle([
        ('BOX', (0, 1), (-1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 1), (-1, -1), 12),
        ('RIGHTPADDING', (0, 1), (-1, -1), 12),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 5),
    ]))
    
    # COLUMNA DERECHA: FINANCIAL SUMMARY
    resumen_data = [
        [Paragraph("<b>SUBTOTAL ..................</b>", style_normal), Paragraph(f"<b>${sub_total:.2f}</b>", style_normal)],
        [Paragraph("<b>IVA 16% ..................</b>", style_normal), Paragraph(f"<b>${iva:.2f}</b>", style_normal)],
        [Paragraph("<b>TOTAL A PAGAR ........</b>", style_normal), Paragraph(f"<b>${total:.2f}</b>", style_normal)],
        [Paragraph("<b>PUEDES ABONAR ........</b>", style_normal), Paragraph(f"<b>${abona_ya:.2f}</b>", style_normal)],
        [Paragraph("<b>Y EN LA ENTREGA ......</b>", style_normal), Paragraph(f"<b>${en_entrega:.2f}</b>", style_normal)],
    ]
    
    # Anchos ajustados para alinear con columna TOTAL de la tabla azul
    # Columna izquierda: 4.68 inches (para que valores queden en posición 8.48 desde borde izquierdo)
    # Columna derecha: 1.0 inches (mismo ancho que columna TOTAL - soporta hasta $99,999.99)
    tabla_resumen = Table(resumen_data, colWidths=[4.68*inch, 1.0*inch])
    tabla_resumen.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),   # Etiquetas alineadas a la derecha
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),   # Valores alineados a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (0, -1), 4),   # Padding izquierdo para etiquetas
        ('RIGHTPADDING', (1, 0), (1, -1), 4),  # Padding derecho para valores
        ('BOX', (0, 0), (1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('BACKGROUND', (0, 2), (1, 2), COLOR_GRIS_CLARO),  # Total destacado
    ]))
    
    # Crear tabla principal de 2 columnas con espacio entre ellas
    # Ajustado para alinear perfectamente con DATOS DEL CLIENTE (9.48 inches total)
    # Columna izquierda: 3.8 inches, Columna derecha: 5.68 inches (más espacio para valores numéricos largos)
    layout_2col_data = [[tabla_col_izq, tabla_resumen]]
    tabla_2col = Table(layout_2col_data, colWidths=[3.8*inch, 5.68*inch])
    tabla_2col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),   # Alinear columna izquierda a la izquierda
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Alinear columna derecha a la derecha
        ('LEFTPADDING', (0, 0), (-1, -1), 0),   # Sin padding izquierdo
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # Sin padding derecho
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    story.append(tabla_2col)
    story.append(Spacer(1, 0.15*inch))
    
    # Bloque de TÉRMINOS Y CONDICIONES eliminado (ahora está en layout de 2 columnas arriba)
    
    # ==========================================
    # PIE DE PÁGINA
    # ==========================================
    
    # Pie de página centrado en el documento
    # Crear estilo centrado para el pie de página
    style_pie = ParagraphStyle(
        'PiePagina',
        parent=style_normal,
        fontSize=7,
        textColor=COLOR_GRIS,
        alignment=TA_CENTER
    )
    
    # Texto con espacios amplios entre las tres frases para mejor legibilidad
    pie_texto = "Generated by <b>LogiPartVE.com</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>www.autoonlinepro.com</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>@repuestosonlinecaracas</b>"
    pie_data = [[
        Paragraph(pie_texto, style_pie),
    ]]
    
    # Ancho completo del documento para centrar el contenido
    tabla_pie = Table(pie_data, colWidths=[9.48*inch])
    tabla_pie.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
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
