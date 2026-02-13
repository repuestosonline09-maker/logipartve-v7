# services/document_generation/__init__.py
"""
Módulo de generación de documentos para LogiPartVE Pro
"""

from .pdf_generator import PDFQuoteGenerator
from .png_generator import PNGQuoteGenerator

__all__ = ['PDFQuoteGenerator', 'PNGQuoteGenerator']
