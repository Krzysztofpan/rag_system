UNTRUSTED_DOCUMENT_START = "<<UNTRUSTED_DOCUMENT>>"
UNTRUSTED_DOCUMENT_END = "<</UNTRUSTED_DOCUMENT>>"


def wrap_untrusted_excerpt(text: str, *, header: str | None = None) -> str:
    lines: list[str] = []
    if header:
        lines.append(header)
    lines.append(UNTRUSTED_DOCUMENT_START)
    lines.append(text.strip())
    lines.append(UNTRUSTED_DOCUMENT_END)
    return "\n".join(lines)


def join_untrusted_context(excerpts: list[str]) -> str:
    return "\n\n---\n\n".join(excerpts)
