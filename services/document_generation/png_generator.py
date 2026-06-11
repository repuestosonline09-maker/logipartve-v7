# services/document_generation/png_generator.py
"""
Generador de PNG para cotizaciones de LogiPartVE Pro.
Convierte cada página del PDF a un PNG de alta calidad.
Soporte multi-página: devuelve una lista de rutas (una por página).
"""

from pdf2image import convert_from_path
import os


class PNGQuoteGenerator:
    """Generador de cotizaciones en formato PNG (multi-página)."""

    def __init__(self):
        self.dpi = 300  # Alta calidad para WhatsApp/Instagram

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL: PDF → lista de PNGs
    # ─────────────────────────────────────────────────────────────────────────
    def generate_quote_png(self, pdf_path, output_path):
        """
        Genera uno o varios PNG de alta calidad desde un PDF.

        Para PDFs de una sola página devuelve la ruta `output_path` tal cual
        (compatibilidad total con el código existente).
        Para PDFs multi-página genera archivos con sufijo _p1, _p2, … y
        devuelve la lista completa de rutas.

        Args:
            pdf_path:    Ruta del PDF fuente.
            output_path: Ruta base donde guardar el/los PNG(s).
                         Ej.: /tmp/logipartve_docs/cotizacion_2026-12345-J.png

        Returns:
            str | list[str] | None:
                - str       → una sola página (comportamiento original)
                - list[str] → varias páginas
                - None      → error
        """
        try:
            images = convert_from_path(pdf_path, dpi=self.dpi, fmt='png')

            if not images:
                print("No se pudieron generar imágenes del PDF")
                return None

            if len(images) == 1:
                # ── Caso original: una sola página ───────────────────────────
                images[0].save(output_path, 'PNG', quality=95, optimize=True)
                return output_path

            # ── Caso multi-página ────────────────────────────────────────────
            base, ext = os.path.splitext(output_path)
            if not ext:
                ext = '.png'

            rutas = []
            for i, img in enumerate(images, 1):
                ruta_pagina = f"{base}_p{i}{ext}"
                img.save(ruta_pagina, 'PNG', quality=95, optimize=True)
                rutas.append(ruta_pagina)

            return rutas

        except Exception as e:
            print(f"Error generando PNG: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO DESDE DATOS: genera PDF temporal y luego convierte a PNG(s)
    # ─────────────────────────────────────────────────────────────────────────
    def generate_quote_png_from_data(self, quote_data, output_path):
        """
        Genera PNG(s) directamente desde los datos de cotización.
        (Genera un PDF temporal y luego lo convierte.)

        Args:
            quote_data:  Diccionario con datos de la cotización.
            output_path: Ruta base donde guardar el/los PNG(s).

        Returns:
            str | list[str] | None: igual que generate_quote_png().
        """
        try:
            from .pdf_generator import PDFQuoteGenerator
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf_path = tmp_pdf.name

            pdf_path = PDFQuoteGenerator.generate(quote_data, tmp_pdf_path)

            if not pdf_path:
                return None

            result = self.generate_quote_png(pdf_path, output_path)

            try:
                os.unlink(tmp_pdf_path)
            except Exception:
                pass

            return result

        except Exception as e:
            print(f"Error generando PNG desde datos: {e}")
            return None
