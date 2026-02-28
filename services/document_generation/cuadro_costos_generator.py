"""
Generador del CUADRO DE COSTOS para LogiPartVE Pro
Genera un PNG de alta calidad con el desglose completo de costos por ítem,
para uso interno administrativo (envío por WhatsApp al grupo admin).
"""

from PIL import Image, ImageDraw, ImageFont
import os
import json
from datetime import datetime

# ── Paleta de colores (consistente con el PDF de cotización) ──────────────────
COLOR_AZUL        = (0,   61,  130)   # #003D82 — azul aviación
COLOR_AZUL_AOP    = (44,  126, 190)   # #2c7ebe — azul logo AOP
COLOR_NARANJA     = (255, 107,  53)   # #FF6B35
COLOR_GRIS_OSC    = (44,   62,  80)   # #2C3E50
COLOR_GRIS_CLARO  = (232, 232, 232)   # #E8E8E8
COLOR_BLANCO      = (255, 255, 255)
COLOR_NEGRO       = (0,   0,   0)
COLOR_VERDE       = (39,  174,  96)   # verde para totales
COLOR_FILA_PAR    = (240, 248, 255)   # azul muy claro para filas pares
COLOR_FILA_IMPAR  = (255, 255, 255)   # blanco para filas impares

# ── Constantes de layout ──────────────────────────────────────────────────────
ANCHO        = 1200   # px
MARGEN_H     = 40     # margen horizontal
MARGEN_V     = 30     # margen vertical superior/inferior
PADDING_CELDA = 10    # padding interior de celdas


def _get_font(size: int, bold: bool = False):
    """Carga una fuente del sistema o usa la fuente por defecto de Pillow."""
    font_paths_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    font_paths_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    paths = font_paths_bold if bold else font_paths_regular
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _texto_ancho(draw, texto: str, fuente) -> int:
    """Devuelve el ancho en píxeles de un texto con la fuente dada."""
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    return bbox[2] - bbox[0]


def _texto_alto(draw, texto: str, fuente) -> int:
    """Devuelve el alto en píxeles de un texto con la fuente dada."""
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    return bbox[3] - bbox[1]


def _fmt_usd(valor) -> str:
    """Formatea un valor numérico como dólares."""
    try:
        return f"${float(valor):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _fmt_pct(valor) -> str:
    """Formatea un valor numérico como porcentaje."""
    try:
        return f"{float(valor):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def generar_cuadro_costos_png(quote_data: dict, items: list, output_path: str) -> str:
    """
    Genera el PNG del Cuadro de Costos.

    Args:
        quote_data : dict con datos de la cotización (quote_number, client_name,
                     client_vehicle, created_at, etc.)
        items      : lista de dicts con los costos de cada ítem
        output_path: ruta donde guardar el PNG

    Returns:
        str: ruta del archivo generado, o None si hay error
    """
    try:
        # ── Fuentes ──────────────────────────────────────────────────────────
        f_titulo    = _get_font(28, bold=True)
        f_subtitulo = _get_font(18, bold=True)
        f_seccion   = _get_font(15, bold=True)
        f_normal    = _get_font(13)
        f_bold      = _get_font(13, bold=True)
        f_small     = _get_font(11)
        f_small_b   = _get_font(11, bold=True)
        f_grande_b  = _get_font(16, bold=True)

        # ── Preparar datos ───────────────────────────────────────────────────
        quote_number  = quote_data.get('quote_number', 'N/A')
        client_name   = quote_data.get('client_name', 'N/A')
        client_vehicle = quote_data.get('client_vehicle', '')
        created_at    = quote_data.get('created_at', '')
        try:
            fecha_str = datetime.fromisoformat(str(created_at)).strftime("%d/%m/%Y")
        except Exception:
            fecha_str = str(created_at)[:10] if created_at else datetime.now().strftime("%d/%m/%Y")

        # ── Calcular altura necesaria ─────────────────────────────────────────
        # Cabecera: logo + título + info general ≈ 180px
        # Por cada ítem: encabezado de ítem (40px) + 14 filas × 26px + separador (10px) ≈ 414px
        ALTO_CABECERA   = 190
        ALTO_ITEM_HEADER = 42
        ALTO_FILA       = 26
        FILAS_POR_ITEM  = 14   # número de conceptos de costo
        ALTO_SEPARADOR  = 16
        ALTO_PIE        = 60

        alto_items = len(items) * (ALTO_ITEM_HEADER + FILAS_POR_ITEM * ALTO_FILA + ALTO_SEPARADOR)
        ALTO_TOTAL = ALTO_CABECERA + alto_items + ALTO_PIE + MARGEN_V * 2

        # ── Crear imagen ─────────────────────────────────────────────────────
        img  = Image.new("RGB", (ANCHO, ALTO_TOTAL), COLOR_BLANCO)
        draw = ImageDraw.Draw(img)

        # ── CABECERA ─────────────────────────────────────────────────────────
        # Banda azul superior
        draw.rectangle([(0, 0), (ANCHO, 90)], fill=COLOR_AZUL)

        # Logo (si existe)
        logo_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "logos", "LOGOLogiPartVE.png"
        )
        logo_path = os.path.normpath(logo_path)
        logo_x = MARGEN_H
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_h = 70
                ratio  = logo_h / logo.height
                logo_w = int(logo.width * ratio)
                logo   = logo.resize((logo_w, logo_h), Image.LANCZOS)
                # Pegar con transparencia
                img.paste(logo, (logo_x, 10), logo)
                logo_x += logo_w + 20
            except Exception:
                pass

        # Título principal en la banda azul
        titulo_txt = "CUADRO DE COSTOS"
        draw.text((ANCHO // 2, 28), titulo_txt, font=f_titulo, fill=COLOR_BLANCO, anchor="mm")
        sub_txt = f"COTIZACIÓN: {quote_number}"
        draw.text((ANCHO // 2, 65), sub_txt, font=f_subtitulo, fill=COLOR_NARANJA, anchor="mm")

        # Banda naranja delgada
        draw.rectangle([(0, 90), (ANCHO, 96)], fill=COLOR_NARANJA)

        # Info general (cliente, vehículo, fecha)
        y_info = 105
        info_col_w = (ANCHO - MARGEN_H * 2) // 3
        campos_info = [
            ("CLIENTE:", client_name),
            ("VEHÍCULO:", client_vehicle or "—"),
            ("FECHA:", fecha_str),
        ]
        for idx, (label, valor) in enumerate(campos_info):
            x_col = MARGEN_H + idx * info_col_w
            draw.text((x_col, y_info), label, font=f_bold, fill=COLOR_AZUL)
            draw.text((x_col, y_info + 20), valor, font=f_normal, fill=COLOR_GRIS_OSC)

        # Línea separadora
        y_sep = y_info + 50
        draw.rectangle([(MARGEN_H, y_sep), (ANCHO - MARGEN_H, y_sep + 2)], fill=COLOR_AZUL_AOP)

        # ── ÍTEMS ─────────────────────────────────────────────────────────────
        y_cursor = y_sep + 12

        # Anchos de columnas de la tabla de conceptos
        COL_LABEL = 340
        COL_VALOR = ANCHO - MARGEN_H * 2 - COL_LABEL

        for idx, item in enumerate(items):
            # Extraer datos del ítem
            descripcion = item.get('descripcion', item.get('description', f'Ítem #{idx+1}'))
            parte       = item.get('parte', item.get('part_number', ''))
            cantidad    = int(item.get('cantidad', item.get('quantity', 1)) or 1)
            costo_fob   = float(item.get('costo_fob', item.get('unit_cost', 0)) or 0)
            fob_total   = float(item.get('fob_total', costo_fob * cantidad) or 0)
            handling    = float(item.get('costo_handling', item.get('international_handling', 0)) or 0)
            manejo      = float(item.get('costo_manejo', item.get('national_handling', 0)) or 0)
            imp_int     = float(item.get('costo_impuesto', 0) or 0)
            imp_pct     = float(item.get('impuesto_porcentaje', item.get('tax_percentage', 0)) or 0)
            utilidad    = float(item.get('utilidad_valor', 0) or 0)
            factor_ut   = float(item.get('factor_utilidad', item.get('profit_factor', 1.0)) or 1.0)
            envio       = float(item.get('costo_envio', item.get('shipping_cost', 0)) or 0)
            tax         = float(item.get('costo_tax', 0) or 0)
            tax_pct     = float(item.get('tax_porcentaje', 0) or 0)
            dif_val     = float(item.get('diferencial_valor', 0) or 0)
            dif_pct     = float(item.get('diferencial_porcentaje', 0) or 0)
            precio_usd  = float(item.get('precio_usd', item.get('total_cost', 0)) or 0)
            precio_bs   = float(item.get('precio_bs', 0) or 0)
            iva_val     = float(item.get('iva_valor', 0) or 0)
            iva_pct     = float(item.get('iva_porcentaje', 0) or 0)
            aplicar_iva = item.get('aplicar_iva', False)

            # ── Encabezado del ítem ──────────────────────────────────────────
            draw.rectangle(
                [(MARGEN_H, y_cursor), (ANCHO - MARGEN_H, y_cursor + ALTO_ITEM_HEADER)],
                fill=COLOR_AZUL_AOP
            )
            item_titulo = f"  ÍTEM #{idx + 1}  —  {descripcion.upper()}"
            if parte:
                item_titulo += f"  |  N° Parte: {parte}"
            draw.text(
                (MARGEN_H + PADDING_CELDA, y_cursor + ALTO_ITEM_HEADER // 2),
                item_titulo,
                font=f_seccion,
                fill=COLOR_BLANCO,
                anchor="lm"
            )
            y_cursor += ALTO_ITEM_HEADER

            # ── Filas de costos ──────────────────────────────────────────────
            conceptos = [
                ("Cantidad de Repuestos",       str(cantidad)),
                ("Costo FOB Unitario",           _fmt_usd(costo_fob)),
                ("Costo FOB Total",              _fmt_usd(fob_total)),
                ("Handling (Internacional)",     _fmt_usd(handling)),
                ("Manejo (Nacional)",            _fmt_usd(manejo)),
                (f"Impuesto Internacional ({_fmt_pct(imp_pct)})", _fmt_usd(imp_int)),
                (f"Utilidad (Factor {factor_ut:.4f})",            _fmt_usd(utilidad)),
                ("Envío",                        _fmt_usd(envio)),
                (f"TAX ({_fmt_pct(tax_pct)})",   _fmt_usd(tax)),
                (f"Diferencial ({_fmt_pct(dif_pct)})", _fmt_usd(dif_val)),
                ("Precio USD (Pago en Dólares)", _fmt_usd(precio_usd)),
                (f"VE Precio Bs {'(con IVA)' if aplicar_iva else '(sin IVA)'}",
                 _fmt_usd(precio_bs)),
                (f"Diferencial de Cambio ({_fmt_pct(dif_pct)})", _fmt_usd(dif_val)),
            ]
            # Agregar IVA solo si aplica
            if aplicar_iva and iva_val > 0:
                conceptos.append((f"IVA Venezuela ({_fmt_pct(iva_pct)})", _fmt_usd(iva_val)))

            for fila_idx, (label, valor) in enumerate(conceptos):
                bg = COLOR_FILA_PAR if fila_idx % 2 == 0 else COLOR_FILA_IMPAR
                y_fila = y_cursor + fila_idx * ALTO_FILA

                # Fondo de fila
                draw.rectangle(
                    [(MARGEN_H, y_fila), (ANCHO - MARGEN_H, y_fila + ALTO_FILA)],
                    fill=bg
                )
                # Línea divisoria horizontal sutil
                draw.line(
                    [(MARGEN_H, y_fila + ALTO_FILA - 1), (ANCHO - MARGEN_H, y_fila + ALTO_FILA - 1)],
                    fill=COLOR_GRIS_CLARO, width=1
                )

                # Columna etiqueta
                draw.text(
                    (MARGEN_H + PADDING_CELDA, y_fila + ALTO_FILA // 2),
                    label,
                    font=f_normal,
                    fill=COLOR_GRIS_OSC,
                    anchor="lm"
                )

                # Columna valor (alineado a la derecha)
                # Destacar filas de totales en verde
                es_total = label.startswith("Precio USD") or label.startswith("VE Precio")
                color_val = COLOR_VERDE if es_total else COLOR_AZUL
                fuente_val = f_bold if es_total else f_normal
                draw.text(
                    (ANCHO - MARGEN_H - PADDING_CELDA, y_fila + ALTO_FILA // 2),
                    valor,
                    font=fuente_val,
                    fill=color_val,
                    anchor="rm"
                )

            y_cursor += len(conceptos) * ALTO_FILA

            # Borde exterior del bloque del ítem
            alto_bloque = ALTO_ITEM_HEADER + len(conceptos) * ALTO_FILA
            draw.rectangle(
                [(MARGEN_H, y_cursor - alto_bloque + ALTO_ITEM_HEADER),
                 (ANCHO - MARGEN_H, y_cursor)],
                outline=COLOR_AZUL_AOP, width=2
            )

            # Separador entre ítems
            y_cursor += ALTO_SEPARADOR

        # ── PIE DE PÁGINA ─────────────────────────────────────────────────────
        draw.rectangle([(0, ALTO_TOTAL - 50), (ANCHO, ALTO_TOTAL)], fill=COLOR_AZUL)
        pie_txt = f"LogiPartVE Pro  •  Cuadro de Costos Interno  •  {datetime.now().strftime('%d/%m/%Y %H:%M')}  •  USO EXCLUSIVO ADMINISTRATIVO"
        draw.text((ANCHO // 2, ALTO_TOTAL - 25), pie_txt, font=f_small, fill=COLOR_BLANCO, anchor="mm")

        # ── Guardar ───────────────────────────────────────────────────────────
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, "PNG", dpi=(150, 150), optimize=True)
        return output_path

    except Exception as e:
        print(f"❌ Error generando Cuadro de Costos PNG: {e}")
        import traceback
        traceback.print_exc()
        return None
