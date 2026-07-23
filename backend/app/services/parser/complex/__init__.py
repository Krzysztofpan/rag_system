"""Docling-based PDF/DOCX extraction with OCR and guarded LLM repair."""

from app.services.parser.complex.converter import build_converter, convert_document
from app.services.parser.complex.parser import ComplexParser
from app.services.parser.complex.postprocess import postprocess_document
from app.services.parser.complex.quality_audit import audit_markdown

__all__ = [
    "ComplexParser",
    "audit_markdown",
    "build_converter",
    "convert_document",
    "postprocess_document",
]
