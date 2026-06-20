"""
Generador de PDF para Cotizaciones - Diseño International Freight
Estilo: Documento de carga aérea internacional
Soporte multi-página: 5 ítems por página, totales solo en la última hoja.
"""

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import os
from pathlib import Path


def clean_text(value) -> str:
    """
    Elimina TODOS los caracteres que ReportLab no puede renderizar.
    Solo permite: letras, numeros, puntuacion ASCII basica y espacio normal.
    Cualquier caracter Unicode especial (espacios raros, caracteres de control,
    formato invisible, etc.) es eliminado o reemplazado por espacio normal.
    """
    if value is None:
        return ''
    text = str(value)
    result = []
    for ch in text:
        code = ord(ch)
        # Espacio ASCII normal: conservar
        if code == 0x20:
            result.append(ch)
        # Caracteres ASCII imprimibles (33-126): conservar
        elif 33 <= code <= 126:
            result.append(ch)
        # Letras y numeros latinos extendidos (acentos, ñ, etc.): conservar
        elif 0xC0 <= code <= 0x024F:
            result.append(ch)
        # Todo lo demas: eliminar (incluye U+00A0, U+200B, U+202F, etc.)
    return ''.join(result).strip()


def find_logo_path(logo_filename):
    """Busca el logo en diferentes ubicaciones posibles."""
    possible_paths = [
        Path(__file__).parent.parent.parent / "assets" / "logos" / logo_filename,
        Path("/app/assets/logos") / logo_filename,
        Path("/tmp/logipartve-v7/assets/logos") / logo_filename,
        Path.cwd() / "assets" / "logos" / logo_filename,
    ]
    for path in possible_paths:
        if path.exists():
            return str(path)
    return None


class InternationalFreightBackground:
    """Clase para dibujar el fondo con marca de agua en cada página."""

    def __init__(self):
        pass

    def draw_watermark(self, canvas_obj, doc):
        """Dibuja la marca de agua con mapa mundial y rutas aéreas."""
        canvas_obj.saveState()

        canvas_obj.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.15)
        canvas_obj.setStrokeColorRGB(0.85, 0.85, 0.85, alpha=0.2)
        canvas_obj.setLineWidth(0.5)

        width = doc.pagesize[0]
        height = doc.pagesize[1]

        for i in range(5, int(height), 40):
            canvas_obj.line(50, i, width - 50, i)

        for i in range(100, int(width), 60):
            canvas_obj.line(i, 50, i, height - 50)

        canvas_obj.setStrokeColorRGB(0.17, 0.49, 0.62, alpha=0.1)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.bezier(150, height - 150, 300, height - 100, 500, height - 120, 650, height - 180)
        canvas_obj.bezier(width - 200, height - 120, width - 350, height - 80, width - 500, height - 150, width - 650, height - 200)

        canvas_obj.setFillColorRGB(0.17, 0.49, 0.62, alpha=0.15)
        canvas_obj.circle(150, height - 150, 8, fill=1)
        canvas_obj.circle(650, height - 180, 8, fill=1)

        canvas_obj.setFont("Helvetica-Bold", 60)
        canvas_obj.setFillColorRGB(0.95, 0.95, 0.95, alpha=0.08)
        canvas_obj.saveState()
        canvas_obj.translate(width / 2, height / 2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, "INTERNATIONAL")
        canvas_obj.drawCentredString(0, -70, "FREIGHT")
        canvas_obj.restoreState()

        canvas_obj.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE DISEÑO
# ─────────────────────────────────────────────────────────────────────────────
ITEMS_POR_PAGINA = 5          # Máximo de ítems por página (preserva el diseño)
MARGEN_H        = 0.3 * inch  # Margen horizontal fijo
MARGEN_V        = 0.2 * inch  # Margen vertical fijo


def _build_styles():
    """Construye y devuelve todos los estilos del documento."""
    styles = getSampleStyleSheet()

    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_AZUL_AOP      = colors.HexColor('#2c7ebe')
    COLOR_GRIS          = colors.HexColor('#2C3E50')

    st_normal = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontSize=8, textColor=colors.black, alignment=TA_LEFT
    )
    st_header = ParagraphStyle(
        'CustomHeader', parent=styles['Normal'],
        fontSize=7, textColor=colors.white,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    st_seccion = ParagraphStyle(
        'CustomSection', parent=styles['Heading2'],
        fontSize=10, textColor=COLOR_AZUL_AVIACION,
        spaceAfter=6, spaceBefore=8,
        fontName='Helvetica-Bold', leftIndent=10
    )
    st_header_titulo = ParagraphStyle(
        'HeaderTitulo', parent=styles['Normal'],
        fontSize=10, textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    st_header_empresa = ParagraphStyle(
        'HeaderEmpresa', parent=styles['Normal'],
        fontSize=11, textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    st_header_direccion = ParagraphStyle(
        'HeaderDireccion', parent=styles['Normal'],
        fontSize=9, textColor=colors.black, alignment=TA_CENTER
    )
    st_header_contacto = ParagraphStyle(
        'HeaderContacto', parent=styles['Normal'],
        fontSize=9, textColor=colors.black, alignment=TA_CENTER
    )
    st_header_web = ParagraphStyle(
        'HeaderWeb', parent=styles['Normal'],
        fontSize=11, textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    st_rif = ParagraphStyle(
        'RifRepresentantes', parent=styles['Normal'],
        fontSize=9, textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    st_pie = ParagraphStyle(
        'PiePagina', parent=styles['Normal'],
        fontSize=7, textColor=COLOR_GRIS, alignment=TA_CENTER
    )
    st_continua = ParagraphStyle(
        'Continua', parent=styles['Normal'],
        fontSize=8, textColor=COLOR_AZUL_AVIACION,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )

    return {
        'normal': st_normal,
        'header': st_header,
        'seccion': st_seccion,
        'header_titulo': st_header_titulo,
        'header_empresa': st_header_empresa,
        'header_direccion': st_header_direccion,
        'header_contacto': st_header_contacto,
        'header_web': st_header_web,
        'rif': st_rif,
        'pie': st_pie,
        'continua': st_continua,
    }


def _build_header_block(st, logos):
    """Construye el bloque de encabezado con logos y datos de la empresa."""
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_GRIS_CLARO    = colors.HexColor('#E8E8E8')

    logo_jdae_path = logos.get('jdae')
    logo_aop_path  = logos.get('aop')
    logo_ig_path   = logos.get('ig')
    logo_fb_path   = logos.get('fb')
    logo_tel_path  = logos.get('tel')
    logo_wa_path   = logos.get('wa')

    bloque_central_data = []
    bloque_central_data.append([Paragraph("✈ <b>COTIZACIÓN INTERNACIONAL DE REPUESTOS</b> ✈", st['header_titulo'])])
    bloque_central_data.append([Paragraph("<b>JDAE AUTO PARTS, C.A.</b>", st['header_empresa'])])
    bloque_central_data.append([Paragraph("Av. Francisco de Miranda cruce con calle Los Laboratorios,", st['header_direccion'])])
    bloque_central_data.append([Paragraph("Centro Empresarial Quorum. Piso 3 ofic 3J. Los Ruices, Caracas.", st['header_direccion'])])

    redes_html = '<para alignment="center">'
    if logo_ig_path:
        redes_html += f'<img src="{logo_ig_path}" width="12" height="12" valign="middle"/> '
    if logo_fb_path:
        redes_html += f'<img src="{logo_fb_path}" width="12" height="12" valign="middle"/> '
    redes_html += '@repuestosonlinecaracas</para>'
    bloque_central_data.append([Paragraph(redes_html, st['header_contacto'])])

    contacto_html = '<para alignment="center">'
    if logo_tel_path:
        contacto_html += f'<img src="{logo_tel_path}" width="12" height="12" valign="middle"/> '
    if logo_wa_path:
        contacto_html += f'<img src="{logo_wa_path}" width="12" height="12" valign="middle"/> '
    contacto_html += 'Contáctanos 0424-1354148</para>'
    bloque_central_data.append([Paragraph(contacto_html, st['header_contacto'])])
    bloque_central_data.append([Paragraph("<b>www.autoonlinepro.com</b>", st['header_web'])])

    tabla_central = Table(bloque_central_data, colWidths=[3.5 * inch])
    tabla_central.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    col_izq_data = []
    if logo_jdae_path:
        col_izq_data.append([Image(logo_jdae_path, width=1.2 * inch, height=1.2 * inch)])
    col_izq_data.append([Paragraph("<b>J-5072639-5</b>", st['rif'])])
    tabla_izq = Table(col_izq_data, colWidths=[1.2 * inch])
    tabla_izq.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    col_der_data = []
    if logo_aop_path:
        col_der_data.append([Image(logo_aop_path, width=1.0 * inch, height=1.0 * inch)])
    col_der_data.append([Paragraph("<b>REPRESENTANTES EXCLUSIVOS<br/>PARA VENEZUELA</b>", st['rif'])])
    tabla_der = Table(col_der_data, colWidths=[1.5 * inch])
    tabla_der.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    header_completo = Table([[tabla_izq, tabla_central, tabla_der]], colWidths=[1.7 * inch, 3.5 * inch, 1.8 * inch])
    header_completo.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return header_completo


def _build_info_doc(st, datos_cotizacion, modo_divisas=False):
    """Construye la barra de información del documento (N° cotización, fecha, asesor)."""
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_GRIS_CLARO    = colors.HexColor('#E8E8E8')

    presupuesto = datos_cotizacion.get('numero_cotizacion') or datos_cotizacion.get('quote_number', 'N/A')
    fecha_raw   = datos_cotizacion.get('fecha', 'N/A')

    if fecha_raw == 'N/A':
        try:
            import sys, os as _os
            sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
            from services.timezone_utils import now_caracas_naive
            fecha_raw = now_caracas_naive().strftime('%Y-%m-%d')
        except Exception:
            from datetime import datetime, timezone, timedelta
            fecha_raw = datetime.now(tz=timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')

    from datetime import datetime
    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').strftime('%d/%m/%y')
    except Exception:
        fecha = fecha_raw

    asesor = datos_cotizacion.get('asesor_ventas') or datos_cotizacion.get('analyst_name', 'N/A')

    if modo_divisas:
        # En modo divisas: la tercera celda muestra la etiqueta PRECIO OPTIMIZADO
        COLOR_VERDE_OPT = colors.HexColor('#006400')  # verde oscuro discreto
        st_opt = ParagraphStyle(
            'PrecioOpt', parent=st['normal'],
            fontSize=8, textColor=COLOR_VERDE_OPT,
            fontName='Helvetica-Bold', alignment=TA_CENTER
        )
        info_doc_data = [[
            Paragraph(f"<b><font color='red'>COTIZACIÓN Nº:</font></b> {presupuesto}", st['normal']),
            Paragraph(f"<b>FECHA:</b> {fecha}", st['normal']),
            Paragraph(f"<b>ASESOR DE VENTAS:</b> {asesor}", st['normal']),
        ],
        [
            Paragraph("", st['normal']),
            Paragraph("", st['normal']),
            Paragraph("<b>★ PRECIO OPTIMIZADO ★</b>", st_opt),
        ]]
        tabla = Table(info_doc_data, colWidths=[3.16 * inch, 3.16 * inch, 3.16 * inch])
        tabla.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 2, COLOR_AZUL_AVIACION),
            ('INNERGRID', (0, 0), (-1, -1), 1, COLOR_GRIS_CLARO),
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS_CLARO),
            ('BACKGROUND', (2, 1), (2, 1), colors.HexColor('#E8F5E9')),  # fondo verde muy claro
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, 1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('SPAN', (0, 1), (1, 1)),  # las dos primeras celdas de la fila 2 se fusionan (vacías)
        ]))
    else:
        info_doc_data = [[
            Paragraph(f"<b><font color='red'>COTIZACIÓN Nº:</font></b> {presupuesto}", st['normal']),
            Paragraph(f"<b>FECHA:</b> {fecha}", st['normal']),
            Paragraph(f"<b>ASESOR DE VENTAS:</b> {asesor}", st['normal']),
        ]]
        tabla = Table(info_doc_data, colWidths=[3.16 * inch, 3.16 * inch, 3.16 * inch])
        tabla.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 2, COLOR_AZUL_AVIACION),
            ('INNERGRID', (0, 0), (-1, -1), 1, COLOR_GRIS_CLARO),
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS_CLARO),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
    return tabla


def _build_cliente_block(st, datos_cotizacion):
    """Construye el bloque de datos del cliente."""
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_GRIS_CLARO    = colors.HexColor('#E8E8E8')

    cliente = datos_cotizacion.get('cliente') or datos_cotizacion.get('client', {})
    vehiculo_completo = cliente.get('vehiculo', '')
    cilindrada = cliente.get('cilindrada') or cliente.get('motor', '')
    if cilindrada:
        vehiculo_completo = f"{vehiculo_completo} {cilindrada}"

    c_nombre    = clean_text(cliente.get('nombre', ''))
    c_ci_rif    = clean_text(cliente.get('ci_rif', ''))
    c_telefono  = clean_text(cliente.get('telefono', ''))
    c_email     = clean_text(cliente.get('email', ''))
    c_direccion = clean_text(cliente.get('direccion', ''))
    c_vehiculo  = clean_text(vehiculo_completo)
    c_año       = clean_text(cliente.get('año', ''))
    c_vin       = clean_text(cliente.get('vin', ''))

    cliente_data = [
        [
            Paragraph(f"<b>NOMBRE:</b> {c_nombre}", st['normal']),
            Paragraph(f"<b>CÉDULA O RIF:</b> {c_ci_rif}", st['normal']),
            Paragraph(f"<b>TELÉFONO:</b> {c_telefono}", st['normal']),
        ],
        [
            Paragraph(f"<b>EMAIL:</b> {c_email}", st['normal']),
            Paragraph(f"<b>DIRECCIÓN:</b> {c_direccion}", st['normal']),
            Paragraph(f"<b>VEHÍCULO:</b> {c_vehiculo}", st['normal']),
        ],
        [
            Paragraph(f"<b>AÑO:</b> {c_año}", st['normal']),
            Paragraph(f"<b>VIN:</b> {c_vin}", st['normal']),
            Paragraph("", st['normal']),
        ],
    ]
    tabla = Table(cliente_data, colWidths=[3.16 * inch, 3.16 * inch, 3.16 * inch])
    tabla.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_CLARO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tabla


def _build_items_table(st, items_slice, item_offset=0, modo_divisas=False):
    """
    Construye la tabla de ítems para una página.

    Args:
        items_slice: Lista de ítems a mostrar en esta página (máx. 5).
        item_offset: Número del primer ítem de esta página (para numeración global).
        modo_divisas: Si True, usa precio_usd (sin diferencial) en lugar de precio_bs.
    """
    COLOR_AZUL_AOP   = colors.HexColor('#2c7ebe')
    COLOR_GRIS_CLARO = colors.HexColor('#E8E8E8')

    items_data = [[
        "ITEM", "DESCRIPCION", "# PARTE", "MARCA", "GARANTIA",
        "QTY", "ENVIO", "ORIGEN", "FABRICACION", "ENTREGA", "UNIT", "TOTAL",
    ]]

    for idx, item in enumerate(items_slice, item_offset + 1):
        cantidad       = item.get('cantidad', 1)
        if modo_divisas:
            # Precio en USD sin diferencial (precio optimizado)
            # precio_usd ya es el total del ítem (incluye cantidad)
            precio_total    = float(item.get('precio_usd', 0) or item.get('precio_usd_total', 0) or 0)
            precio_unitario = precio_total / cantidad if cantidad > 0 else 0
        else:
            precio_total    = item.get('precio_bs', 0)
            precio_unitario = precio_total / cantidad if cantidad > 0 else 0
        descripcion    = item.get('descripcion', '') or item.get('descripcion_repuesto', '')
        # Red de seguridad: truncar a 50 caracteres para proteger el diseño
        descripcion = str(descripcion)
        if len(descripcion) > 50:
            descripcion = descripcion[:47] + '...'

        items_data.append([
            Paragraph(str(idx), st['normal']),
            Paragraph(descripcion, st['normal']),
            Paragraph(str(item.get('parte', '')), st['normal']),
            Paragraph(str(item.get('marca', '')), st['normal']),
            Paragraph(str(item.get('garantia', '')), st['normal']),
            Paragraph(str(item.get('cantidad', '')), st['normal']),
            Paragraph(str(item.get('envio_tipo', '')), st['normal']),
            Paragraph(str(item.get('origen', '')), st['normal']),
            Paragraph(str(item.get('fabricacion', '')), st['normal']),
            Paragraph(str(item.get('tiempo_entrega', '')), st['normal']),
            Paragraph(f"${precio_unitario:.2f}", st['normal']),
            Paragraph(f"${precio_total:.2f}", st['normal']),
        ])

    # ── Compresión dinámica calibrada para 5 ítems en una hoja ──────────────
    _max_desc = 0
    _max_part = 0
    for item in items_slice:
        desc  = str(item.get('descripcion', '') or item.get('descripcion_repuesto', ''))
        parte = str(item.get('parte', ''))
        orig  = str(item.get('origen', ''))
        _max_desc = max(_max_desc, len(desc), len(orig))
        _max_part = max(_max_part, len(parte))

    density = len(items_slice)
    if _max_desc > 15:  density += 1
    if _max_desc > 30:  density += 1
    if _max_desc > 60:  density += 1
    if _max_desc > 100: density += 1
    if _max_part > 15:  density += 1
    if _max_part > 30:  density += 1

    if density <= 2:
        fh, fc, pv = 6.5, 7.0, 4
    elif density <= 3:
        fh, fc, pv = 6.0, 6.5, 3
    elif density <= 4:
        fh, fc, pv = 5.5, 6.0, 2
    elif density <= 6:
        fh, fc, pv = 5.0, 5.5, 1
    elif density <= 8:
        fh, fc, pv = 4.5, 5.0, 1
    else:
        fh, fc, pv = 4.0, 4.5, 1

    col_widths = [0.4*inch, 1.7*inch, 0.95*inch, 0.85*inch, 0.6*inch,
                  0.4*inch, 0.6*inch, 0.7*inch, 0.78*inch, 0.5*inch, 1.0*inch, 1.0*inch]

    tabla = Table(items_data, colWidths=col_widths)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_AZUL_AOP),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), fh),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), fc),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),
        ('ALIGN', (10, 1), (10, -1), 'RIGHT'),
        ('ALIGN', (11, 1), (11, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_AZUL_AOP),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_CLARO),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
        ('TOPPADDING',    (0, 0), (-1, -1), pv),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pv),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tabla


def _build_footer_block(st):
    """Construye el pie de página estándar."""
    COLOR_GRIS = colors.HexColor('#2C3E50')
    pie_texto = (
        "Generated by <b>LogiPartVE.com</b>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        "<b>www.autoonlinepro.com</b>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        "<b>@repuestosonlinecaracas</b>"
    )
    pie_data = [[Paragraph(pie_texto, st['pie'])]]
    tabla = Table(pie_data, colWidths=[9.48 * inch])
    tabla.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
    ]))
    return tabla


def _build_continua_block(st, pagina_siguiente):
    """
    Construye el bloque de nota de continuación para páginas intermedias.
    Reemplaza el espacio de totales en páginas que no son la última.
    """
    COLOR_AZUL_AOP      = colors.HexColor('#2c7ebe')
    COLOR_GRIS_CLARO    = colors.HexColor('#E8E8E8')

    nota_texto = (
        f"&#9658; Ver totales en la página {pagina_siguiente}"
    )
    nota_data = [[Paragraph(nota_texto, st['continua'])]]
    tabla = Table(nota_data, colWidths=[9.48 * inch])
    tabla.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1.0, COLOR_AZUL_AOP),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS_CLARO),
    ]))
    return tabla


def _build_totales_block(st, datos_cotizacion, modo_divisas=False):
    """Construye el bloque de Términos + Financial Summary (solo en la última página)."""
    COLOR_AZUL_AVIACION = colors.HexColor('#003D82')
    COLOR_GRIS_CLARO    = colors.HexColor('#E8E8E8')

    if modo_divisas:
        # Totales en USD sin diferencial
        sub_total  = datos_cotizacion.get('total_usd_divisas', datos_cotizacion.get('sub_total', 0))
        iva        = 0  # En modo divisas no se aplica IVA
        total      = sub_total
        abona_ya   = datos_cotizacion.get('usd_abono', 0)
        en_entrega = datos_cotizacion.get('usd_entrega', 0)
    else:
        sub_total  = datos_cotizacion.get('sub_total', 0)
        iva        = datos_cotizacion.get('iva_total', 0)
        total      = datos_cotizacion.get('total_a_pagar', 0)
        abona_ya   = datos_cotizacion.get('abona_ya', 0)
        en_entrega = datos_cotizacion.get('y_en_entrega', 0)

    terminos_raw  = datos_cotizacion.get('terminos_condiciones', 'Términos y condiciones estándar')
    terminos_html = terminos_raw.replace('\n', '<br/>')

    st_seccion = st['seccion']
    st_normal  = st['normal']

    # Columna izquierda: Términos
    col_izq_data = [
        [Paragraph("<b>▼ TÉRMINOS Y CONDICIONES</b>", st_seccion)],
        [Paragraph(terminos_html, st_normal)],
    ]
    tabla_col_izq = Table(col_izq_data, colWidths=[3.8 * inch])
    tabla_col_izq.setStyle(TableStyle([
        ('BOX', (0, 1), (-1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 1), (-1, -1), 8),
        ('RIGHTPADDING', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 5),
    ]))

    # Columna derecha: Financial Summary
    if modo_divisas:
        # En modo divisas: sin fila de IVA, etiqueta TOTAL en verde
        COLOR_VERDE_OPT = colors.HexColor('#006400')
        st_opt = ParagraphStyle(
            'PrecioOptTotal', parent=st_normal,
            fontSize=8, textColor=COLOR_VERDE_OPT, fontName='Helvetica-Bold'
        )
        resumen_data = [
            [Paragraph("<b>TOTAL USD ................</b>", st_normal),         Paragraph(f"<b>${total:.2f}</b>",      st_normal)],
            [Paragraph("<b>PUEDES ABONAR ........</b>", st_normal),             Paragraph(f"<b>${abona_ya:.2f}</b>",   st_normal)],
            [Paragraph("<b>Y EN LA ENTREGA ......</b>", st_normal),             Paragraph(f"<b>${en_entrega:.2f}</b>", st_normal)],
        ]
    else:
        resumen_data = [
            [Paragraph("<b>SUBTOTAL ..................</b>", st_normal),  Paragraph(f"<b>${sub_total:.2f}</b>",  st_normal)],
            [Paragraph("<b>IVA 16% ..................</b>", st_normal),   Paragraph(f"<b>${iva:.2f}</b>",        st_normal)],
            [Paragraph("<b>TOTAL A PAGAR ........</b>", st_normal),      Paragraph(f"<b>${total:.2f}</b>",      st_normal)],
            [Paragraph("<b>PUEDES ABONAR ........</b>", st_normal),      Paragraph(f"<b>${abona_ya:.2f}</b>",   st_normal)],
            [Paragraph("<b>Y EN LA ENTREGA ......</b>", st_normal),      Paragraph(f"<b>${en_entrega:.2f}</b>", st_normal)],
        ]
    tabla_resumen = Table(resumen_data, colWidths=[4.68 * inch, 1.0 * inch])
    tabla_resumen.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (0, -1), 4),
        ('RIGHTPADDING', (1, 0), (1, -1), 4),
        ('BOX', (0, 0), (1, -1), 1.5, COLOR_AZUL_AVIACION),
        ('BACKGROUND', (0, 2), (1, 2), COLOR_GRIS_CLARO),
    ]))

    layout_2col = Table([[tabla_col_izq, tabla_resumen]], colWidths=[3.8 * inch, 5.68 * inch])
    layout_2col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return layout_2col


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def _generar_pagina_pdf(datos_cotizacion, items_slice, num_pagina, total_paginas,
                        logos, st, output_path, modo_divisas=False):
    """
    Genera un PDF de UNA SOLA PÁGINA con el contenido especificado.
    Cada página se genera de forma independiente para garantizar que
    el header siempre aparezca al inicio de cada hoja.
    """
    es_ultima = (num_pagina == total_paginas)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        rightMargin=MARGEN_H,
        leftMargin=MARGEN_H,
        topMargin=MARGEN_V,
        bottomMargin=MARGEN_V,
    )

    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    story.append(_build_header_block(st, logos))
    story.append(Spacer(1, 0.01 * inch))

    # ── INFO DOCUMENTO ───────────────────────────────────────────────────────
    story.append(_build_info_doc(st, datos_cotizacion, modo_divisas=modo_divisas))
    story.append(Spacer(1, 0.08 * inch))

    # ── DATOS DEL CLIENTE ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("▼ DATOS DEL CLIENTE", st['seccion']))
    story.append(_build_cliente_block(st, datos_cotizacion))
    story.append(Spacer(1, 0.05 * inch))

    # ── TABLA DE ÍTEMS ──────────────────────────────────────────────────────────────────────
    item_offset = (num_pagina - 1) * ITEMS_POR_PAGINA
    story.append(_build_items_table(st, items_slice, item_offset, modo_divisas=modo_divisas))
    story.append(Spacer(1, 0.08 * inch))

    # ── TOTALES o NOTA DE CONTINUACIÓN ────────────────────────────────────────────────────────────
    if es_ultima:
        story.append(_build_totales_block(st, datos_cotizacion, modo_divisas=modo_divisas))
    else:
        story.append(_build_continua_block(st, num_pagina + 1))

    story.append(Spacer(1, 0.08 * inch))

    # ── PIE DE PÁGINA ────────────────────────────────────────────────────────
    story.append(_build_footer_block(st))

    # Generar con marca de agua
    background = InternationalFreightBackground()
    doc.build(
        story,
        onFirstPage=background.draw_watermark,
        onLaterPages=background.draw_watermark,
    )

    return output_path


def generar_pdf_cotizacion(datos_cotizacion, output_path, modo_divisas=False):
    """
    Genera un PDF multi-página con el diseño International Freight.

    Estrategia: cada página se genera como un PDF independiente de una sola
    hoja y luego se fusionan en un único archivo. Esto garantiza que el
    header completo aparezca al inicio de cada página sin interferencia
    del motor de flujo de ReportLab.

    Args:
        datos_cotizacion: Diccionario con los datos de la cotización.
        output_path: Ruta donde se guardará el PDF.

    Returns:
        str: Ruta del archivo PDF generado.
    """
    import tempfile
    from pypdf import PdfWriter, PdfReader

    # Cargar logos una sola vez
    logos = {
        'jdae': find_logo_path("LOGOJDAEAUTOPARTES.png"),
        'aop':  find_logo_path("LogoAutoOnlinePro.png"),
        'fb':   find_logo_path("LOGOFACEBOOK.png"),
        'ig':   find_logo_path("LOGOINSTAGRAM.png"),
        'tel':  find_logo_path("LOGOTELEFONO.png"),
        'wa':   find_logo_path("LOGOWHATSAPP.png"),
    }

    # Construir estilos una sola vez
    st = _build_styles()

    # Obtener todos los ítems y dividir en páginas
    todos_items = datos_cotizacion.get('items', [])
    paginas = []
    for i in range(0, max(len(todos_items), 1), ITEMS_POR_PAGINA):
        paginas.append(todos_items[i:i + ITEMS_POR_PAGINA])

    total_paginas = len(paginas)

    if total_paginas == 1:
        # ── Caso simple: una sola página (comportamiento original) ────────────
        return _generar_pagina_pdf(
            datos_cotizacion, paginas[0], 1, 1,
            logos, st, output_path, modo_divisas=modo_divisas
        )

    # ── Caso multi-página: generar cada hoja por separado y fusionar ──────────
    writer = PdfWriter()
    tmp_files = []

    try:
        for num_pagina, items_slice in enumerate(paginas, 1):
            # Archivo temporal para esta página
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=f'_p{num_pagina}.pdf')
            os.close(tmp_fd)
            tmp_files.append(tmp_path)

            # Generar la página individual
            _generar_pagina_pdf(
                datos_cotizacion, items_slice, num_pagina, total_paginas,
                logos, st, tmp_path, modo_divisas=modo_divisas
            )

            # Agregar la página al writer
            reader = PdfReader(tmp_path)
            for page in reader.pages:
                writer.add_page(page)

        # Escribir el PDF fusionado final
        with open(output_path, 'wb') as f:
            writer.write(f)

    finally:
        # Limpiar archivos temporales
        for tmp_path in tmp_files:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# CLASE WRAPPER PARA COMPATIBILIDAD
# ─────────────────────────────────────────────────────────────────────────────
class PDFQuoteGenerator:
    """Clase wrapper para mantener compatibilidad con el código existente."""

    @staticmethod
    def generate(datos_cotizacion, output_path):
        """
        Genera un PDF de cotización (modo BCV estándar).

        Args:
            datos_cotizacion: Diccionario con los datos de la cotización.
            output_path: Ruta donde se guardará el PDF.

        Returns:
            str: Ruta del archivo PDF generado.
        """
        return generar_pdf_cotizacion(datos_cotizacion, output_path, modo_divisas=False)

    @staticmethod
    def generate_divisas(datos_cotizacion, output_path):
        """
        Genera un PDF de cotización en modo PRECIO OPTIMIZADO (divisas USD).
        Los precios por ítem y totales se muestran en USD sin diferencial.
        Incluye etiqueta discreta '★ PRECIO OPTIMIZADO ★' en la barra de info.

        Args:
            datos_cotizacion: Diccionario con los datos de la cotización.
                              Debe incluir 'usd_abono', 'usd_entrega' y 'total_usd_divisas'.
            output_path: Ruta donde se guardará el PDF.

        Returns:
            str: Ruta del archivo PDF generado.
        """
        return generar_pdf_cotizacion(datos_cotizacion, output_path, modo_divisas=True)
