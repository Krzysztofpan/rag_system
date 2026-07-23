from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument

from .postprocess import postprocess_document


def build_converter() -> DocumentConverter:
    """Build a Docling converter tuned for digital PDFs with tables."""
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        images_scale=2.0,
    )
    pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=False)
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True,
    )

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def convert_document(
    source: Path | str,
    *,
    page_range: tuple[int, int] | None = None,
    ocr_repair: bool = True,
    llm_repair: bool = True,
    llm_model: str | None = None,
) -> DoclingDocument:
    """Convert a PDF or DOCX and run the repair pipeline."""
    source_path = Path(source)
    converter = build_converter()
    kwargs: dict = {"source": str(source_path)}
    if page_range is not None:
        kwargs["page_range"] = page_range

    result = converter.convert(**kwargs)
    return postprocess_document(
        result.document,
        source_path=source_path,
        ocr_repair=ocr_repair,
        llm_repair=llm_repair,
        llm_model=llm_model,
    )
