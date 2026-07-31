import pytest

from app.services.parser.base import ParseQualityError
from app.services.parser.complex.ocr_repair import MISSING_GLYPH, REPLACEMENT_CHAR
from app.services.parser.complex.quality_audit import (
    audit_markdown,
    chunk_defect_kinds,
    ensure_chunk_quality,
    evaluate_chunk_quality,
)
from tests.helpers import make_chunk


def test_audit_markdown_clean_text():
    report = audit_markdown("# Title\n\nClean paragraph.")
    assert report["ok"] is True
    assert report["counts"] == {}
    assert report["issues"] == []


def test_audit_markdown_detects_soft_and_critical_defects():
    markdown = "\n".join(
        [
            f"broken glyph {REPLACEMENT_CHAR} here",
            "price is 12 3 dollars",
            "the word re fi nery appears",
        ]
    )
    report = audit_markdown(markdown)
    assert report["ok"] is False
    assert "unresolved_glyph" in report["counts"]
    assert "split_number" in report["counts"]
    assert "broken_fi_fl" in report["counts"]


def test_chunk_defect_kinds_only_flags_critical_glyphs():
    assert chunk_defect_kinds(f"bad {MISSING_GLYPH}") == ["unresolved_glyph"]
    assert chunk_defect_kinds(f"bad {REPLACEMENT_CHAR}") == ["unresolved_glyph"]
    assert chunk_defect_kinds("price is 12 3 dollars") == []
    assert chunk_defect_kinds("the word re fi nery") == []


def test_evaluate_chunk_quality_keeps_clean_chunks():
    chunks = [make_chunk("alpha"), make_chunk("beta")]
    quality = evaluate_chunk_quality(chunks, max_rejected_ratio=0.25)
    assert quality["ok"] is True
    assert quality["kept_indexes"] == [0, 1]
    assert quality["rejected_chunks"] == 0


def test_evaluate_chunk_quality_rejects_document_above_threshold():
    chunks = [
        make_chunk(f"bad {REPLACEMENT_CHAR}"),
        make_chunk("good"),
        make_chunk(f"also bad {MISSING_GLYPH}"),
        make_chunk("fine"),
    ]
    quality = evaluate_chunk_quality(chunks, max_rejected_ratio=0.25)
    # 2/4 = 0.5 >= 0.25
    assert quality["ok"] is False
    assert quality["kept_indexes"] == [1, 3]
    assert quality["rejected_chunks"] == 2


def test_evaluate_chunk_quality_empty_chunks_is_not_ok():
    quality = evaluate_chunk_quality([], max_rejected_ratio=0.25)
    assert quality["ok"] is False
    assert quality["rejected_ratio"] == 1.0


def test_ensure_chunk_quality_filters_rejected_below_threshold():
    chunks = [
        make_chunk("good one"),
        make_chunk(f"bad {REPLACEMENT_CHAR}"),
        make_chunk("good two"),
        make_chunk("good three"),
        make_chunk("good four"),
    ]
    kept, quality = ensure_chunk_quality(
        chunks,
        parse_report={"ok": True},
        max_rejected_ratio=0.25,
    )
    assert [c.content for c in kept] == ["good one", "good two", "good three", "good four"]
    assert quality["rejected_chunks"] == 1
    assert quality["ok"] is True


def test_ensure_chunk_quality_raises_parse_quality_error():
    chunks = [
        make_chunk(f"bad {REPLACEMENT_CHAR}"),
        make_chunk("only one good"),
    ]
    with pytest.raises(ParseQualityError, match="Document rejected") as exc_info:
        ensure_chunk_quality(
            chunks,
            parse_report={"ok": False, "counts": {"unresolved_glyph": 1}},
            max_rejected_ratio=0.25,
        )

    assert "chunk_quality" in exc_info.value.report
    assert exc_info.value.document_id is None
