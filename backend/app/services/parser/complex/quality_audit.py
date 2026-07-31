from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING

from app.config import get_settings
from app.services.parser.base import ParseQualityError

from .ocr_repair import MISSING_GLYPH, REPLACEMENT_CHAR

if TYPE_CHECKING:
    from app.services.chunker.base import ChunkResult


_CHECKS = {
    "unresolved_glyph": re.compile(f"[{MISSING_GLYPH}{REPLACEMENT_CHAR}]"),
    "split_number": re.compile(r"\b\d{2,}\s+\d\b"),
    "broken_fi_fl": re.compile(r"\b\w{2,}\s+(?:fi|fl)\s+\w{2,}\b", re.I),
}

# Only these defects drop a chunk; softer warnings stay in the document report.
_CRITICAL_CHUNK_CHECKS = {
    "unresolved_glyph": _CHECKS["unresolved_glyph"],
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


def chunk_defect_kinds(text: str) -> list[str]:
    """Critical parse defects that make a chunk unsafe to index."""
    return [
        kind for kind, pattern in _CRITICAL_CHUNK_CHECKS.items() if pattern.search(text)
    ]


def evaluate_chunk_quality(
    chunks: list["ChunkResult"],
    *,
    max_rejected_ratio: float,
) -> dict[str, object]:
    """Score chunk-level quality and decide whether the document can be kept.

    Soft document warnings (split numbers, fi/fl breaks) do not drop chunks.
    Unresolved glyphs do: those chunks are rejected individually. The whole
    document is rejected only when the rejected-chunk ratio reaches the threshold.
    """
    kept_indexes: list[int] = []
    rejected: list[dict[str, object]] = []

    for index, chunk in enumerate(chunks):
        kinds = chunk_defect_kinds(chunk.content)
        if kinds:
            rejected.append(
                {
                    "index": index,
                    "kinds": kinds,
                    "text": chunk.content[:500],
                }
            )
        else:
            kept_indexes.append(index)

    total = len(chunks)
    rejected_count = len(rejected)
    rejected_ratio = (rejected_count / total) if total else 1.0
    ok = total > 0 and rejected_ratio < max_rejected_ratio

    return {
        "ok": ok,
        "total_chunks": total,
        "kept_chunks": len(kept_indexes),
        "rejected_chunks": rejected_count,
        "rejected_ratio": rejected_ratio,
        "max_rejected_ratio": max_rejected_ratio,
        "kept_indexes": kept_indexes,
        "rejected": rejected,
    }


def ensure_chunk_quality(
    chunks: list["ChunkResult"],
    *,
    parse_report: dict,
    max_rejected_ratio: float | None = None,
) -> tuple[list["ChunkResult"], dict[str, object]]:
    """Keep clean chunks or reject the document when quality is too poor.

    Returns (kept_chunks, chunk_quality). Raises ParseQualityError when the
    rejected-chunk ratio reaches the configured threshold.
    """
    if max_rejected_ratio is None:
        max_rejected_ratio = get_settings().parser_max_rejected_chunk_ratio

    chunk_quality = evaluate_chunk_quality(
        chunks,
        max_rejected_ratio=max_rejected_ratio,
    )
    report = {
        **parse_report,
        "chunk_quality": chunk_quality,
    }

    if not chunk_quality["ok"]:
        rejected = chunk_quality["rejected_chunks"]
        total = chunk_quality["total_chunks"]
        ratio = chunk_quality["rejected_ratio"]
        threshold = chunk_quality["max_rejected_ratio"]
        raise ParseQualityError(
            (
                f"Document rejected: {rejected}/{total} chunks "
                f"({ratio:.0%}) failed quality checks "
                f"(threshold {threshold:.0%})"
            ),
            report=report,
        )

    kept_indexes = chunk_quality["kept_indexes"]
    kept = [chunks[i] for i in kept_indexes]
    return kept, chunk_quality
