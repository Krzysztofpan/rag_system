"""Placeholder characters for failed PDF glyph extraction.

Kept in a tiny module so quality_audit can import them without pulling
RapidOCR/Docling (ocr_repair.py). Markdown ingest must stay on this path.
"""

# Docling sentinel when the PDF font has no glyph for a character.
MISSING_GLYPH = "\uffff"

# Unicode replacement character (U+FFFD) when a byte cannot be decoded.
REPLACEMENT_CHAR = "\ufffd"
