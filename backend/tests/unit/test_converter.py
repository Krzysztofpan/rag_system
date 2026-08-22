from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.pipeline.vlm_pipeline import VlmPipeline

from app.services.parser.complex.converter import build_converter, convert_document


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "parser_image_pipeline": "vlm",
        "openai_api_key": "sk-test",
        "parser_vlm_model": "gpt-4o-mini",
        "parser_vlm_timeout": 90,
        "parser_vlm_url": "https://api.openai.com/v1/chat/completions",
        "parser_image_suffixes": (".png", ".jpg", ".jpeg"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_converter_vlm_image_uses_openai():
    converter = build_converter(_settings())
    image_option = converter.format_to_options[InputFormat.IMAGE]

    assert InputFormat.IMAGE in converter.allowed_formats
    assert image_option.pipeline_cls is VlmPipeline
    assert image_option.pipeline_options.enable_remote_services is True
    assert isinstance(image_option.pipeline_options.vlm_options, ApiVlmOptions)
    assert image_option.pipeline_options.vlm_options.params["model"] == "gpt-4o-mini"
    assert str(image_option.pipeline_options.vlm_options.url).rstrip("/") == (
        "https://api.openai.com/v1/chat/completions"
    )


def test_build_converter_standard_image_uses_ocr():
    converter = build_converter(
        _settings(parser_image_pipeline="standard", openai_api_key=None)
    )
    image_option = converter.format_to_options[InputFormat.IMAGE]

    assert image_option.pipeline_cls is StandardPdfPipeline


def test_build_converter_vlm_requires_openai_key():
    with pytest.raises(ValueError, match="OpenAI API key"):
        build_converter(_settings(openai_api_key=None))


@patch("app.services.parser.complex.converter.postprocess_document")
@patch("app.services.parser.complex.converter.build_converter")
@patch("app.services.parser.complex.converter.get_settings")
def test_convert_document_skips_llm_repair_for_vlm_images(
    get_settings, build, postprocess, tmp_path
):
    get_settings.return_value = _settings()
    fake_doc = SimpleNamespace()
    converter = MagicMock()
    converter.convert.return_value = SimpleNamespace(document=fake_doc)
    build.return_value = converter
    postprocess.return_value = fake_doc

    source = tmp_path / "photo.png"
    source.write_bytes(b"x")
    convert_document(source, llm_repair=True)

    assert postprocess.call_args.kwargs["llm_repair"] is False


@patch("app.services.parser.complex.converter.postprocess_document")
@patch("app.services.parser.complex.converter.build_converter")
@patch("app.services.parser.complex.converter.get_settings")
def test_convert_document_keeps_llm_repair_for_pdf(
    get_settings, build, postprocess, tmp_path
):
    get_settings.return_value = _settings()
    fake_doc = SimpleNamespace()
    converter = MagicMock()
    converter.convert.return_value = SimpleNamespace(document=fake_doc)
    build.return_value = converter
    postprocess.return_value = fake_doc

    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF")
    convert_document(source, llm_repair=True)

    assert postprocess.call_args.kwargs["llm_repair"] is True
