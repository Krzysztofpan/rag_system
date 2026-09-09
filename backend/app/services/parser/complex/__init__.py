"""Docling-based PDF/DOCX extraction with OCR and guarded LLM repair.

Heavy Docling/RapidOCR imports stay in submodules and load only when a
complex parser or converter is actually used.
"""

from typing import Any

__all__ = [
    "ComplexParser",
    "audit_markdown",
    "ensure_chunk_quality",
    "build_converter",
    "convert_document",
    "postprocess_document",
]


def __getattr__(name: str) -> Any:
    if name in {"audit_markdown", "ensure_chunk_quality"}:
        from app.services.parser.complex.quality_audit import (
            audit_markdown,
            ensure_chunk_quality,
        )

        return audit_markdown if name == "audit_markdown" else ensure_chunk_quality
    if name == "ComplexParser":
        from app.services.parser.complex.parser import ComplexParser

        return ComplexParser
    if name in {"build_converter", "convert_document"}:
        from app.services.parser.complex.converter import (
            build_converter,
            convert_document,
        )

        return build_converter if name == "build_converter" else convert_document
    if name == "postprocess_document":
        from app.services.parser.complex.postprocess import postprocess_document

        return postprocess_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
