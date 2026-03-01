"""
Generador del CUADRO DE COSTOS para LogiPartVE Pro
Formato HORIZONTAL: conceptos en filas, ítems en columnas.
Genera un PNG de alta calidad para uso interno administrativo
(envío por WhatsApp al grupo admin).
"""

from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

# ── Paleta de colores ─────────────────────────────────────────────────────────
COLOR_AZUL        = (0,   61,  130)   # azul oscuro corporativo
COLOR_AZUL_MED    = (44,  126, 190)   # azul medio (encabezados de ítem)
COLOR_AZUL_SUAVE  = (210, 230, 250)   # azul muy claro (fila de encabezado de concepto)
COLOR_NARANJA     = (255, 107,  53)   # naranja corporativo
COLOR_GRIS_OSC    = (44,   62,  80)   # texto oscuro
COLOR_GRIS_CLARO  = (220, 220, 220)   # líneas de separación
COLOR_BLANCO      = (255, 255, 255)
COLOR_VERDE       = (27,  153,  81)   # totales en USD
COLOR_VERDE_SUAVE = (220, 245, 230)   # fondo fila totales
COLOR_AMARILLO    = (255, 248, 220)   # fondo fila TOTAL COMPRA
COLOR_FILA_PAR    = (240, 248, 255)
COLOR_FILA_IMPAR  = (255, 255, 255)
COLOR_TOTAL_BG    = (0,   80,  160)   # fondo celda TOTAL COMPRA en header


def _get_font(size: int, bold: bool = False):
    """Carga una fuente del sistema o usa la fuente por defecto de Pillow."""
    paths_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    paths_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in (paths_bold if bold else paths_reg):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fmt_usd(valor) -> str:
    try:
        return f"${float(valor):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _fmt_pct(valor) -> str:
    try:
        return f"{float(valor):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _draw_text_centered(draw, text, x, y, w, h, font, color):
    """Dibuja texto centrado dentro de un rectángulo (x, y, x+w, y+h)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, font=font, fill=color)


def _draw_text_right(draw, text, x, y, w, h, font, color):
    """Dibuja texto alineado a la derecha dentro de un rectángulo."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + w - tw - 8
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, font=font, fill=color)


def _draw_text_left(draw, text, x, y, w, h, font, color):
    """Dibuja texto alineado a la izquierda dentro de un rectángulo."""
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]
    ty = y + (h - th) // 2
    draw.text((x + 8, ty), text, font=font, fill=color)


def generar_cuadro_costos_png(quote_data: dict, items: list, output_path: str) -> str:
    """
    Genera el PNG del Cuadro de Costos en formato HORIZONTAL.

    Layout:
      - Encabezado: logo | título | número cotización | info cliente/vehículo/fecha | TOTAL COMPRA
      - Tabla:
          Columna 0 (fija): nombre del concepto
          Columnas 1..N:    valores por ítem
          Columna N+1:      (vacía / reservada para futuro)

    Filas de conceptos (en orden):
      1  Cantidad de Repuestos
      2  Costo FOB Unitario
      3  Costo FOB Total
      4  Handling (Internacional)
      5  Manejo (Nacional)
      6  Impuesto Internacional (X%)
      7  Utilidad (Factor X)
      8  Envío
      9  TAX (X%)
      10 Diferencial de Cambio (X%)
      11 Precio USD (Pago en Dólares)       ← verde, negrita
      12 VE Precio Bs (con/sin IVA)         ← verde, negrita
    """
    try:
        # ── Fuentes ──────────────────────────────────────────────────────────
        f_titulo    = _get_font(26, bold=True)
        f_subtitulo = _get_font(17, bold=True)
        f_info_lbl  = _get_font(12, bold=True)
        f_info_val  = _get_font(12)
        f_th        = _get_font(12, bold=True)   # encabezado columna ítem
        f_concepto  = _get_font(12)              # etiqueta de concepto (col 0)
        f_valor     = _get_font(12)              # valor normal
        f_valor_b   = _get_font(12, bold=True)   # valor destacado (totales)
        f_total_lbl = _get_font(13, bold=True)
        f_total_val = _get_font(16, bold=True)
        f_pie       = _get_font(10)

        # ── Datos generales ──────────────────────────────────────────────────
        quote_number   = quote_data.get('quote_number', 'N/A')
        client_name    = quote_data.get('client_name', 'N/A')
        client_vehicle = quote_data.get('client_vehicle', '—')
        created_at     = quote_data.get('created_at', '')
        try:
            fecha_str = datetime.fromisoformat(str(created_at)).strftime("%d/%m/%Y")
        except Exception:
            fecha_str = datetime.now().strftime("%d/%m/%Y")

        n_items = len(items)

        # ── Dimensiones de la tabla ──────────────────────────────────────────
        MARGEN        = 36
        ALTO_FILA     = 28
        ALTO_HEADER_T = 44    # fila de encabezado de ítems (nombres de columna)
        COL0_W        = 260   # ancho columna de conceptos
        COL_ITEM_W    = 160   # ancho de cada columna de ítem
        ALTO_CABECERA = 175   # altura del bloque de encabezado superior
        ALTO_PIE      = 44

        # Conceptos de costo (etiqueta, clave_valor, es_total)
        # clave_valor se usa para extraer el dato del dict del ítem
        CONCEPTOS = [
            ("Cantidad de Repuestos",        "cantidad",          False),
            ("Costo FOB Unitario",            "costo_fob",         False),
            ("Costo FOB Total",               "fob_total",         False),
            ("Handling (Internacional)",      "costo_handling",    False),
            ("Manejo (Nacional)",             "costo_manejo",      False),
            ("Impuesto Internacional",        "costo_impuesto",    False),
            ("Utilidad",                      "utilidad_valor",    False),
            ("Envío",                         "costo_envio",       False),
            ("TAX",                           "costo_tax",         False),
            ("Diferencial de Cambio",         "diferencial_valor", False),
            ("Precio USD (Pago en Dólares)",  "precio_usd",        True),
            ("VE Precio Bs",                  "precio_bs",         True),
        ]
        N_FILAS = len(CONCEPTOS)

        # ── Calcular TOTAL COMPRA ─────────────────────────────────────────────
        # Suma de: FOB Total + Handling + Manejo + Impuesto + Utilidad + Envío + TAX
        # (para TODOS los ítems)
        total_compra = 0.0
        for item in items:
            total_compra += (
                float(item.get('fob_total',       0) or 0) +
                float(item.get('costo_handling',  0) or 0) +
                float(item.get('costo_manejo',    0) or 0) +
                float(item.get('costo_impuesto',  0) or 0) +
                float(item.get('utilidad_valor',  0) or 0) +
                float(item.get('costo_envio',     0) or 0) +
                float(item.get('costo_tax',       0) or 0)
            )

        # ── Ancho total de la imagen ─────────────────────────────────────────
        TABLA_W  = COL0_W + COL_ITEM_W * n_items
        ANCHO    = max(MARGEN * 2 + TABLA_W, 900)
        # Centrar la tabla si la imagen es más ancha
        tabla_x  = (ANCHO - TABLA_W) // 2

        # ── Alto total de la imagen ──────────────────────────────────────────
        ALTO_TABLA = ALTO_HEADER_T + N_FILAS * ALTO_FILA
        ALTO       = ALTO_CABECERA + ALTO_TABLA + ALTO_PIE + 20

        # ── Crear imagen ─────────────────────────────────────────────────────
        img  = Image.new("RGB", (ANCHO, ALTO), COLOR_BLANCO)
        draw = ImageDraw.Draw(img)

        # ════════════════════════════════════════════════════════════════════
        # BLOQUE CABECERA
        # ════════════════════════════════════════════════════════════════════

        # Banda azul oscuro superior
        draw.rectangle([(0, 0), (ANCHO, 85)], fill=COLOR_AZUL)

        # Logo
        logo_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "logos", "LOGOLogiPartVE.png"
        ))
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                lh = 65
                lw = int(logo.width * lh / logo.height)
                logo = logo.resize((lw, lh), Image.LANCZOS)
                img.paste(logo, (MARGEN, 10), logo)
            except Exception:
                pass

        # Título centrado en la banda
        _draw_text_centered(draw, "CUADRO DE COSTOS",
                            0, 8, ANCHO, 38, f_titulo, COLOR_BLANCO)
        _draw_text_centered(draw, f"COTIZACIÓN: {quote_number}",
                            0, 50, ANCHO, 30, f_subtitulo, COLOR_NARANJA)

        # Banda naranja delgada
        draw.rectangle([(0, 85), (ANCHO, 91)], fill=COLOR_NARANJA)

        # ── Fila de info: CLIENTE | VEHÍCULO | FECHA | TOTAL COMPRA ──────────
        y_info = 98
        H_INFO = 70

        # Dividir en 4 bloques: los 3 primeros iguales, el 4to más ancho
        bloque_w    = (ANCHO - MARGEN * 2) // 4
        bloque_tc_w = ANCHO - MARGEN * 2 - bloque_w * 3   # puede ser igual o mayor

        campos = [
            ("CLIENTE:",   client_name),
            ("VEHÍCULO:",  client_vehicle or "—"),
            ("FECHA:",     fecha_str),
        ]
        for i, (lbl, val) in enumerate(campos):
            bx = MARGEN + i * bloque_w
            draw.text((bx, y_info),      lbl, font=f_info_lbl, fill=COLOR_AZUL)
            draw.text((bx, y_info + 20), val, font=f_info_val, fill=COLOR_GRIS_OSC)

        # Bloque TOTAL COMPRA (esquina superior derecha)
        tc_x = MARGEN + bloque_w * 3
        tc_w = ANCHO - MARGEN - tc_x
        # Fondo destacado
        draw.rectangle([(tc_x - 8, y_info - 6), (ANCHO - MARGEN + 8, y_info + H_INFO - 10)],
                       fill=COLOR_TOTAL_BG, outline=COLOR_NARANJA, width=2)
        _draw_text_centered(draw, "TOTAL COMPRA",
                            tc_x - 8, y_info - 6, tc_w + 16, 24, f_total_lbl, COLOR_NARANJA)
        _draw_text_centered(draw, _fmt_usd(total_compra),
                            tc_x - 8, y_info + 18, tc_w + 16, 36, f_total_val, COLOR_BLANCO)

        # Línea separadora
        y_sep = y_info + H_INFO
        draw.rectangle([(MARGEN, y_sep), (ANCHO - MARGEN, y_sep + 2)], fill=COLOR_AZUL_MED)

        # ════════════════════════════════════════════════════════════════════
        # TABLA HORIZONTAL
        # ════════════════════════════════════════════════════════════════════
        y_tabla = y_sep + 10

        # ── Fila de encabezado de ítems ──────────────────────────────────────
        # Celda vacía col 0
        draw.rectangle(
            [(tabla_x, y_tabla), (tabla_x + COL0_W, y_tabla + ALTO_HEADER_T)],
            fill=COLOR_AZUL
        )
        _draw_text_centered(draw, "CONCEPTO / ÍTEM",
                            tabla_x, y_tabla, COL0_W, ALTO_HEADER_T,
                            f_th, COLOR_BLANCO)

        # Celdas de encabezado por ítem
        for idx, item in enumerate(items):
            cx = tabla_x + COL0_W + idx * COL_ITEM_W
            desc = item.get('descripcion', item.get('description', f'Ítem #{idx+1}'))
            # Truncar descripción si es muy larga
            if len(desc) > 18:
                desc = desc[:16] + "…"
            draw.rectangle(
                [(cx, y_tabla), (cx + COL_ITEM_W, y_tabla + ALTO_HEADER_T)],
                fill=COLOR_AZUL_MED
            )
            # Número de ítem
            _draw_text_centered(draw, f"ÍTEM #{idx+1}",
                                cx, y_tabla, COL_ITEM_W, 20, f_th, COLOR_BLANCO)
            # Descripción truncada
            _draw_text_centered(draw, desc,
                                cx, y_tabla + 20, COL_ITEM_W, ALTO_HEADER_T - 20,
                                _get_font(10), COLOR_BLANCO)

            # Borde derecho
            draw.line([(cx + COL_ITEM_W, y_tabla),
                       (cx + COL_ITEM_W, y_tabla + ALTO_HEADER_T)],
                      fill=COLOR_BLANCO, width=1)

        # Borde inferior del encabezado
        draw.line([(tabla_x, y_tabla + ALTO_HEADER_T),
                   (tabla_x + TABLA_W, y_tabla + ALTO_HEADER_T)],
                  fill=COLOR_BLANCO, width=2)

        # ── Filas de datos ───────────────────────────────────────────────────
        for fila_idx, (concepto, clave, es_total) in enumerate(CONCEPTOS):
            y_fila = y_tabla + ALTO_HEADER_T + fila_idx * ALTO_FILA

            # Color de fondo de la fila
            if es_total:
                bg = COLOR_VERDE_SUAVE
            elif fila_idx % 2 == 0:
                bg = COLOR_FILA_PAR
            else:
                bg = COLOR_FILA_IMPAR

            # Fondo completo de la fila
            draw.rectangle(
                [(tabla_x, y_fila), (tabla_x + TABLA_W, y_fila + ALTO_FILA)],
                fill=bg
            )

            # ── Celda col 0: nombre del concepto ────────────────────────────
            # Agregar porcentaje al concepto si aplica
            label = concepto
            if clave == "costo_impuesto" and items:
                pct = items[0].get('impuesto_porcentaje', 0)
                label = f"{concepto} ({_fmt_pct(pct)})"
            elif clave == "costo_tax" and items:
                pct = items[0].get('tax_porcentaje', 7.0)
                label = f"{concepto} ({_fmt_pct(pct)})"
            elif clave == "diferencial_valor" and items:
                pct = items[0].get('diferencial_porcentaje', 0)
                label = f"{concepto} ({_fmt_pct(pct)})"
            elif clave == "utilidad_valor" and items:
                factor = items[0].get('factor_utilidad', 1.0)
                label = f"{concepto} (Factor {float(factor):.4f})"
            elif clave == "precio_bs" and items:
                aplica_iva = items[0].get('aplicar_iva', False)
                label = f"{concepto} ({'con IVA' if aplica_iva else 'sin IVA'})"

            fuente_concepto = f_valor_b if es_total else f_concepto
            color_concepto  = COLOR_VERDE if es_total else COLOR_GRIS_OSC
            _draw_text_left(draw, label,
                            tabla_x, y_fila, COL0_W, ALTO_FILA,
                            fuente_concepto, color_concepto)

            # Línea divisoria col 0 / datos
            draw.line([(tabla_x + COL0_W, y_fila),
                       (tabla_x + COL0_W, y_fila + ALTO_FILA)],
                      fill=COLOR_GRIS_CLARO, width=1)

            # ── Celdas de valores por ítem ───────────────────────────────────
            for idx, item in enumerate(items):
                cx = tabla_x + COL0_W + idx * COL_ITEM_W
                raw = item.get(clave, 0) or 0

                if clave == "cantidad":
                    txt = str(int(float(raw)))
                    fuente_val = f_valor_b if es_total else f_valor
                    color_val  = COLOR_VERDE if es_total else COLOR_GRIS_OSC
                    _draw_text_centered(draw, txt, cx, y_fila, COL_ITEM_W, ALTO_FILA,
                                        fuente_val, color_val)
                else:
                    txt = _fmt_usd(raw)
                    fuente_val = f_valor_b if es_total else f_valor
                    color_val  = COLOR_VERDE if es_total else COLOR_AZUL
                    _draw_text_right(draw, txt, cx, y_fila, COL_ITEM_W, ALTO_FILA,
                                     fuente_val, color_val)

                # Separador vertical entre ítems
                draw.line([(cx + COL_ITEM_W, y_fila),
                           (cx + COL_ITEM_W, y_fila + ALTO_FILA)],
                          fill=COLOR_GRIS_CLARO, width=1)

            # Línea horizontal inferior de la fila
            draw.line([(tabla_x, y_fila + ALTO_FILA),
                       (tabla_x + TABLA_W, y_fila + ALTO_FILA)],
                      fill=COLOR_GRIS_CLARO, width=1)

        # ── Borde exterior de la tabla ────────────────────────────────────────
        draw.rectangle(
            [(tabla_x, y_tabla),
             (tabla_x + TABLA_W, y_tabla + ALTO_HEADER_T + N_FILAS * ALTO_FILA)],
            outline=COLOR_AZUL_MED, width=2
        )

        # ════════════════════════════════════════════════════════════════════
        # PIE DE PÁGINA
        # ════════════════════════════════════════════════════════════════════
        y_pie = ALTO - ALTO_PIE
        draw.rectangle([(0, y_pie), (ANCHO, ALTO)], fill=COLOR_AZUL)
        pie_txt = (
            f"LogiPartVE Pro  •  Cuadro de Costos Interno  •  "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}  •  USO EXCLUSIVO ADMINISTRATIVO"
        )
        _draw_text_centered(draw, pie_txt, 0, y_pie, ANCHO, ALTO_PIE, f_pie, COLOR_BLANCO)

        # ── Guardar ───────────────────────────────────────────────────────────
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, "PNG", dpi=(150, 150), optimize=True)
        return output_path

    except Exception as e:
        print(f"❌ Error generando Cuadro de Costos PNG: {e}")
        import traceback
        traceback.print_exc()
        return None
