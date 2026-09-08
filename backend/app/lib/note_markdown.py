from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from app.schemas.resource import ChatNoteContent, parse_note_content

_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\\/:*?"<>|]+')
_BLOCK_TAGS = frozenset({
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ul",
    "ol",
    "tr",
    "blockquote",
    "pre",
    "br",
})


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS and tag != "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)


def html_to_text(html: str) -> str:
    parser = _HTMLTextParser()
    parser.feed(html)
    parser.close()
    text = "".join(parser._parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def note_body_text(content: dict[str, Any] | None) -> str:
    parsed = parse_note_content(content)
    if isinstance(parsed, ChatNoteContent):
        return parsed.markdown.strip()
    return html_to_text(parsed.html)


def note_source_markdown(title: str, content: dict[str, Any] | None) -> str:
    body = note_body_text(content)
    if not body:
        return ""
    heading = title.strip() or "New Note"
    return f"# {heading}\n\n{body}\n"


def source_filename_from_title(title: str) -> str:
    stem = _UNSAFE_FILENAME_CHARS.sub("-", title.strip())
    stem = re.sub(r"-{2,}", "-", stem).strip("-. ") or "New Note"
    return f"{stem}.md"
