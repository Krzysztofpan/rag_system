from __future__ import annotations

from pathlib import Path

from docling_core.types.doc.document import DoclingDocument

from .llm_repair import DEFAULT_MODEL, repair_document_with_llm
from .ocr_repair import repair_missing_glyphs_with_ocr
from .table_repair import repair_split_table_columns


def postprocess_document(
    doc: DoclingDocument,
    *,
    source_path: Path | str,
    ocr_repair: bool = True,
    llm_repair: bool = True,
    llm_model: str | None = None,
) -> DoclingDocument:
    path = Path(source_path)
    # Targeted OCR needs a PDF rasterization path (PyMuPDF).
    if ocr_repair and path.suffix.lower() == ".pdf":
        repair_missing_glyphs_with_ocr(doc, path)
    repair_split_table_columns(doc)
    repair_document_with_llm(
        doc,
        enabled=llm_repair,
        model=llm_model or DEFAULT_MODEL,
    )
    return doc
