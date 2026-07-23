"""Docling-based PDF/DOCX extraction with OCR and guarded LLM repair."""

from .converter import build_converter, convert_document
from .postprocess import postprocess_document
from .quality_audit import audit_markdown

__all__ = [
    "audit_markdown",
    "build_converter",
    "convert_document",
    "postprocess_document",
]
