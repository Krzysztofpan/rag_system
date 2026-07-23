from __future__ import annotations

import re
from collections import Counter

from .ocr_repair import MISSING_GLYPH, REPLACEMENT_CHAR


_CHECKS = {
    "unresolved_glyph": re.compile(f"[{MISSING_GLYPH}{REPLACEMENT_CHAR}]"),
    "split_number": re.compile(r"\b\d{2,}\s+\d\b"),
    "broken_fi_fl": re.compile(r"\b\w{2,}\s+(?:fi|fl)\s+\w{2,}\b", re.I),
}


def audit_markdown(markdown: str) -> dict[str, object]:
    """Return structural extraction warnings without guessing replacements."""
    issues: list[dict[str, object]] = []
    for line_no, line in enumerate(markdown.splitlines(), start=1):
        kinds = [kind for kind, pattern in _CHECKS.items() if pattern.search(line)]
        if not kinds:
            continue
        issues.append(
            {
                "line": line_no,
                "kinds": kinds,
                "text": line[:500],
            }
        )

    counts = Counter(kind for issue in issues for kind in issue["kinds"])
    return {
        "ok": not issues,
        "counts": dict(sorted(counts.items())),
        "issues": issues,
    }
