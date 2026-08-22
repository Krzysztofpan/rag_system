from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
    TableStructureOptions,
    VlmPipelineOptions,
)
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling_core.types.doc.document import DoclingDocument

from app.config import Settings, get_settings

from .postprocess import postprocess_document

_VLM_IMAGE_PROMPT = (
    "Convert the image to clean Markdown. Preserve headings, lists and tables. "
    "Describe charts/diagrams. Do not invent text."
)


def _pdf_pipeline_options() -> PdfPipelineOptions:
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        images_scale=2.0,
    )
    pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=False)
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True,
    )
    return pipeline_options


def _image_format_option(settings: Settings) -> ImageFormatOption:
    if settings.parser_image_pipeline == "standard":
        return ImageFormatOption(pipeline_options=_pdf_pipeline_options())

    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OpenAI API key is required for VLM image parsing")

    return ImageFormatOption(
        pipeline_cls=VlmPipeline,
        pipeline_options=VlmPipelineOptions(
            enable_remote_services=True,
            force_backend_text=False,
            vlm_options=ApiVlmOptions(
                url=settings.parser_vlm_url,
                headers={"Authorization": f"Bearer {api_key}"},
                params={"model": settings.parser_vlm_model},
                timeout=settings.parser_vlm_timeout,
                response_format=ResponseFormat.MARKDOWN,
                prompt=_VLM_IMAGE_PROMPT,
                temperature=0.0,
                scale=2.0,
            ),
        ),
    )


def build_converter(settings: Settings | None = None) -> DocumentConverter:
    """Build a Docling converter for PDFs, DOCX, and images."""
    settings = settings or get_settings()
    pdf_options = _pdf_pipeline_options()
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.IMAGE],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            InputFormat.IMAGE: _image_format_option(settings),
        },
    )


def convert_document(
    source: Path | str,
    *,
    page_range: tuple[int, int] | None = None,
    ocr_repair: bool = True,
    llm_repair: bool = True,
    llm_model: str | None = None,
) -> DoclingDocument:
    """Convert a PDF, DOCX, or image and run the repair pipeline."""
    settings = get_settings()
    source_path = Path(source)
    converter = build_converter(settings)
    kwargs: dict = {"source": str(source_path)}
    if page_range is not None:
        kwargs["page_range"] = page_range

    if (
        source_path.suffix.lower() in settings.parser_image_suffixes
        and settings.parser_image_pipeline == "vlm"
    ):
        llm_repair = False

    result = converter.convert(**kwargs)
    return postprocess_document(
        result.document,
        source_path=source_path,
        ocr_repair=ocr_repair,
        llm_repair=llm_repair,
        llm_model=llm_model,
    )
