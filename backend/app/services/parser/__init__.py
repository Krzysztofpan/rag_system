"""Document parsing: factory, simple text parsers, and Docling complex pipeline."""

from typing import Any

from app.services.parser.base import (
    ParseQualityError,
    ParseResult,
    Parser,
)
from app.services.parser.factory import ParserFactory
from app.services.parser.simple import SimpleParser
from app.lib.file_types import FileTypes

__all__ = [
    "ComplexParser",
    "FileTypes",
    "ParseQualityError",
    "ParseResult",
    "Parser",
    "ParserFactory",
    "SimpleParser",
]


def __getattr__(name: str) -> Any:
    if name == "ComplexParser":
        from app.services.parser.complex.parser import ComplexParser

        return ComplexParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
