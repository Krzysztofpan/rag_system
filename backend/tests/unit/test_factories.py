import pytest

from app.services.chunker.complex import ComplexChunker
from app.services.chunker.factory import ChunkerFactory
from app.services.chunker.simple import SimpleChunker
from app.services.parser.complex.parser import ComplexParser
from app.services.parser.factory import ParserFactory
from app.services.parser.simple import SimpleParser
from app.types import FileTypes
from tests.helpers import make_upload_file


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        (FileTypes.MD, SimpleParser),
        (FileTypes.TXT, SimpleParser),
        (FileTypes.PDF, ComplexParser),
        (FileTypes.DOCX, ComplexParser),
    ],
)
def test_parser_factory_routes_by_mime(content_type, expected):
    upload = make_upload_file("body", content_type=content_type, filename="f")
    parser = ParserFactory.create_parser(upload)
    assert isinstance(parser, expected)


def test_parser_factory_rejects_unknown_mime():
    upload = make_upload_file("body", content_type="application/zip", filename="f.zip")
    with pytest.raises(ValueError, match="Unexpected file type"):
        ParserFactory.create_parser(upload)


def test_parser_factory_rejects_missing_mime():
    upload = make_upload_file("body", content_type="", filename="f")
    with pytest.raises(ValueError, match="Unexpected file type"):
        ParserFactory.create_parser(upload)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        (FileTypes.MD, SimpleChunker),
        (FileTypes.TXT, SimpleChunker),
        (FileTypes.PDF, ComplexChunker),
        (FileTypes.DOCX, ComplexChunker),
    ],
)
def test_chunker_factory_routes_by_mime(content_type, expected):
    chunker = ChunkerFactory.create_chunker(content_type)
    assert isinstance(chunker, expected)


def test_chunker_factory_rejects_unknown_mime():
    with pytest.raises(ValueError, match="Unexpected file type"):
        ChunkerFactory.create_chunker("image/png")
