from __future__ import annotations

import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import fitz
import numpy as np
from docling_core.types.doc.base import BoundingBox, CoordOrigin
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table_data import TableCell
from docling_core.types.doc.items.text import TextItem
from rapidocr import RapidOCR

MISSING_GLYPH = "\uffff"
REPLACEMENT_CHAR = "\ufffd"
_MISSING_CHARS = {MISSING_GLYPH, REPLACEMENT_CHAR}
_FI_SUFFIXES = r"rst|gure|nd|ed|ltration|cial|ngertips|ned|ciently"
_PLACEHOLDER = r"(?:\uffff|\ufffd)"
_PLACEHOLDER_RUN = rf"{_PLACEHOLDER}(?:\s*{_PLACEHOLDER})*"
_PAGE_OCR_CACHE: dict[tuple[str, int], str] = {}
_BBOX_OCR_CACHE: dict[tuple[object, ...], str] = {}


def text_needs_ocr_repair(text: str) -> bool:
    return MISSING_GLYPH in text or REPLACEMENT_CHAR in text


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_numeric_spacing(text: str) -> str:
    text = re.sub(r"(\d)\s+\.\s+(\d)", r"\1.\2", text)
    text = re.sub(r"(\d)\s+:", r"\1:", text)
    return text


def _split_placeholder_parts(text: str) -> list[tuple[str, bool]]:
    """Split text into (segment, is_placeholder_run) parts."""
    parts: list[tuple[str, bool]] = []
    last = 0
    for match in re.finditer(_PLACEHOLDER_RUN, text):
        if match.start() > last:
            parts.append((text[last : match.start()], False))
        parts.append((match.group(0), True))
        last = match.end()
    if last < len(text):
        parts.append((text[last:], False))
    return parts


def _anchor_regex(segment: str) -> re.Pattern[str] | None:
    tokens = _normalize_ws(segment).split()
    if not tokens:
        return None
    return re.compile(r"\s+".join(re.escape(token) for token in tokens), re.I)


def _fuzzy_find_in_ocr(
    ocr: str,
    segment: str,
    *,
    start: int,
    edge: str,
) -> tuple[int, int] | None:
    """Locate an anchor despite a small OCR typo, returning OCR character offsets."""
    ocr_words = list(re.finditer(r"\w+", ocr[start:], flags=re.UNICODE))
    anchor_words = re.findall(r"\w+", segment, flags=re.UNICODE)
    if not ocr_words or not anchor_words:
        return None

    anchor_words = anchor_words[-8:] if edge == "end" else anchor_words[:8]
    anchor = " ".join(anchor_words).casefold()
    expected_len = len(anchor_words)
    threshold = 0.9 if expected_len == 1 else 0.72
    best: tuple[float, int, int] | None = None

    for word_index in range(len(ocr_words)):
        for window_len in range(max(1, expected_len - 1), expected_len + 2):
            window = ocr_words[word_index : word_index + window_len]
            if len(window) != window_len:
                continue
            candidate = " ".join(match.group(0) for match in window).casefold()
            score = SequenceMatcher(None, anchor, candidate).ratio()
            if score < threshold:
                continue
            begin = start + window[0].start()
            end = start + window[-1].end()
            if best is None or score > best[0]:
                best = (score, begin, end)

    return None if best is None else (best[1], best[2])


def _find_in_ocr(
    ocr: str,
    segment: str,
    *,
    start: int = 0,
    edge: str = "start",
) -> tuple[int, int] | None:
    """Locate a known text segment using exact and typo-tolerant anchors."""
    segment = _normalize_ws(segment)
    if not segment:
        return (start, start)

    candidates: list[str] = []
    if len(segment) > 48:
        candidates.append(segment[-80:] if edge == "end" else segment[:80])
    candidates.append(segment)

    for candidate in candidates:
        pattern = _anchor_regex(candidate)
        if pattern is None:
            continue
        match = pattern.search(ocr, pos=start)
        if match:
            return match.start(), match.end()
    return _fuzzy_find_in_ocr(ocr, segment, start=start, edge=edge)


def _normalize_placeholder_fill(
    placeholder_run: str,
    fill: str,
    *,
    left_context: str = "",
    right_context: str = "",
) -> str:
    """Normalize OCR text that replaces a placeholder run."""
    fill = _normalize_ws(fill)
    if not fill:
        return ""

    run_len = max(_placeholder_run_len(placeholder_run), 1)
    compact = re.sub(r"\s+", "", fill)

    # An inline gap can cause OCR to return the whole word. Remove the readable
    # fragments on both sides, leaving only the glyph(s) absent from PDF text.
    left_fragment = re.search(r"(\w+)\s*$", left_context, flags=re.UNICODE)
    right_fragment = re.match(r"^\s*(\w+)", right_context, flags=re.UNICODE)
    if left_fragment and compact.casefold().startswith(left_fragment.group(1).casefold()):
        compact = compact[len(left_fragment.group(1)) :]
    if right_fragment and compact.casefold().endswith(right_fragment.group(1).casefold()):
        compact = compact[: -len(right_fragment.group(1))]
    if compact:
        fill = compact

    # If the OCR span between anchors is huge, the right anchor likely missed —
    # prefer a short numeric/version/ligature token instead of dumping a sentence.
    if len(compact) > max(8, run_len * 6):
        # Multi-glyph holes are digits/versions only — never grab leading letters
        # from misaligned OCR ("Thye..." → "Thy" for a Top ￿￿ hole).
        if run_len >= 2:
            short = re.match(r"[vV]?\d+(?:\.\d+)*", fill)
        else:
            short = re.match(r"[vV]?\d+(?:\.\d+)*|[A-Za-z]{1,3}", fill)
        if not short:
            return ""
        fill = short.group(0)
        compact = re.sub(r"\s+", "", fill)

    # Pure numbers / dotted versions: drop OCR spacing artifacts ("2 . 1 . 0").
    if re.fullmatch(r"\d+(\.\d+)*", compact):
        return compact
    if re.fullmatch(r"[vV]\d+(\.\d+)+", compact):
        return compact
    # Multi-glyph runs encode digits/years ("10", "2025") — alphabetic fills
    # are almost always misaligned OCR and must not clear the placeholders.
    if run_len >= 2:
        return ""
    # Short alphabetic fills are typically ligatures (fi/fl) or a single letter.
    if re.fullmatch(r"[A-Za-z0-9]{1,3}", compact):
        return compact
    return fill


def _placeholder_run_len(run: str) -> int:
    return sum(1 for ch in run if ch in _MISSING_CHARS)


def fill_placeholders_from_ocr(original: str, ocr: str) -> str:
    """
    Recover missing glyphs by aligning known text anchors with OCR.

    Works for any PDF: placeholder runs are replaced with the OCR span that sits
    between the surrounding readable anchors. No document-specific vocab.
    """
    if not ocr or not text_needs_ocr_repair(original):
        return original

    ocr_norm = _normalize_ws(ocr)
    parts = _split_placeholder_parts(original)
    if not any(is_ph for _, is_ph in parts):
        return original

    out: list[str] = []
    ocr_pos = 0
    left_anchor_found = False

    for index, (segment, is_placeholder) in enumerate(parts):
        if not is_placeholder:
            anchor = segment
            if index + 1 < len(parts) and parts[index + 1][1] and not segment[-1:].isspace():
                anchor = re.sub(r"\w+$", "", segment, flags=re.UNICODE)
            located = _find_in_ocr(ocr_norm, anchor, start=ocr_pos, edge="end")
            if located is not None:
                ocr_pos = located[1]
                left_anchor_found = True
            else:
                left_anchor_found = False
            out.append(segment)
            continue

        right = ""
        for next_segment, next_is_ph in parts[index + 1 :]:
            if not next_is_ph:
                right = next_segment
                break

        end_bound = len(ocr_norm)
        right_anchor_found = False
        if _normalize_ws(right):
            right_anchor = right
            if not right[:1].isspace():
                right_anchor = re.sub(r"^\w+", "", right, flags=re.UNICODE)
            right_anchor = _normalize_ws(right_anchor)[:80]
            located = _find_in_ocr(
                ocr_norm,
                right_anchor,
                start=ocr_pos,
                edge="start",
            )
            if located is not None:
                end_bound = located[0]
                right_anchor_found = True

        raw_fill = (
            ocr_norm[ocr_pos:end_bound]
            if left_anchor_found or right_anchor_found
            else ""
        )
        left = parts[index - 1][0] if index > 0 and not parts[index - 1][1] else ""
        fill = _normalize_placeholder_fill(
            segment,
            raw_fill,
            left_context=left,
            right_context=right,
        )
        if fill:
            out.append(fill)
            # PDF extractors often put spaces around every missing glyph. If a
            # recovered digit run directly continues with a readable digit,
            # keep it as one number (e.g. four missing digits followed by "8").
            if fill[-1:].isdigit() and re.match(r"^\s+\d", right):
                parts[index + 1] = (right.lstrip(), False)
            ocr_pos = end_bound
        else:
            out.append(segment)

    return "".join(out)


def _repair_fi_ligatures(text: str) -> str:
    """
    Replace remaining single placeholders that are clearly fi/fl ligatures.

    Multi-glyph runs are left alone — those are usually digits/numbers and must
    come from OCR, not ligature heuristics.
    """
    # fl before "ow" (flow, flower, ...)
    text = re.sub(
        rf"(?<=\w)\s*{_PLACEHOLDER}\s*(?=ow\b)",
        "fl",
        text,
    )
    # Known fi suffixes after a single placeholder.
    text = re.sub(
        rf"(?<=-)\s*{_PLACEHOLDER}\s*(?={_FI_SUFFIXES})",
        "fi",
        text,
    )
    text = re.sub(
        rf"(?<![0-9{MISSING_GLYPH}{REPLACEMENT_CHAR}])"
        rf"{_PLACEHOLDER}"
        rf"(?!\s*(?:{_PLACEHOLDER}|[0-9]))"
        rf"\s*(?={_FI_SUFFIXES})",
        "fi",
        text,
    )
    # Single placeholder between letters (not digits, not another placeholder).
    text = re.sub(
        rf"(?<=[A-Za-z])\s*{_PLACEHOLDER}\s*(?=[A-Za-z])",
        "fi",
        text,
    )
    return text


def _clean_missing_glyphs(text: str) -> str:
    return text.replace(MISSING_GLYPH, "").replace(REPLACEMENT_CHAR, "")


def _has_likely_numeric_gap(text: str) -> bool:
    if any(
        _placeholder_run_len(match.group(0)) >= 2
        for match in re.finditer(_PLACEHOLDER_RUN, text)
    ):
        return True
    return bool(
        re.search(rf"(?:[vV]\s*{_PLACEHOLDER}|{_PLACEHOLDER}\s*[.\d])", text)
    )


@lru_cache(maxsize=1)
def _get_ocr_engine() -> RapidOCR:
    return RapidOCR()


def _bbox_to_fitz_rect(bbox: BoundingBox, page_height: float) -> fitz.Rect:
    if bbox.coord_origin == CoordOrigin.BOTTOMLEFT:
        return fitz.Rect(bbox.l, page_height - bbox.t, bbox.r, page_height - bbox.b)
    return fitz.Rect(bbox.l, bbox.t, bbox.r, bbox.b)


def _ocr_image(img: np.ndarray) -> str:
    result = _get_ocr_engine()(img)
    if not result.txts:
        return ""
    return " ".join(result.txts).strip()


def ocr_bbox_region(
    pdf_path: Path | str,
    page_no: int,
    bbox: BoundingBox,
    *,
    scale: float = 3.0,
    pad: float = 3.0,
) -> str:
    key = (
        str(Path(pdf_path).resolve()),
        page_no,
        bbox.l,
        bbox.t,
        bbox.r,
        bbox.b,
        bbox.coord_origin,
        scale,
        pad,
    )
    cached = _BBOX_OCR_CACHE.get(key)
    if cached is not None:
        return cached

    pdf = fitz.open(str(pdf_path))
    try:
        page = pdf[page_no - 1]
        rect = _bbox_to_fitz_rect(bbox, page.rect.height)
        clip = fitz.Rect(
            max(0, rect.x0 - pad),
            max(0, rect.y0 - pad),
            min(page.rect.width, rect.x1 + pad),
            min(page.rect.height, rect.y1 + pad),
        )
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        text = _ocr_image(img)
    finally:
        pdf.close()
    _BBOX_OCR_CACHE[key] = text
    return text


def ocr_page_text(
    pdf_path: Path | str,
    page_no: int,
    *,
    scale: float = 2.0,
) -> str:
    """Full-page OCR with cache — general fallback when bbox OCR is too narrow."""
    key = (str(Path(pdf_path).resolve()), page_no)
    cached = _PAGE_OCR_CACHE.get(key)
    if cached is not None:
        return cached

    pdf = fitz.open(str(pdf_path))
    try:
        page = pdf[page_no - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        text = _ocr_image(img)
    finally:
        pdf.close()

    _PAGE_OCR_CACHE[key] = text
    return text


def _ocr_is_better(original: str, candidate: str) -> bool:
    """
    Decide whether a full OCR string may replace the original item text.

    Must stay roughly the same length as the item — page OCR often contains
    neighboring blocks (headings, checklists) and must not be pasted wholesale.
    """
    if not candidate or text_needs_ocr_repair(candidate):
        return False
    if re.search(r"\s{3,}", candidate):
        return False

    cleaned = _clean_missing_glyphs(original)
    if _has_likely_numeric_gap(original):
        original_digit_chars = len(re.sub(r"\D", "", original))
        candidate_digit_chars = len(re.sub(r"\D", "", candidate))
        if candidate_digit_chars <= original_digit_chars:
            return False
    if len(candidate) < len(cleaned) * 0.85:
        return False
    # Reject over-long OCR (e.g. full-page OCR that swallowed the checklist).
    if len(candidate) > max(len(cleaned) * 1.35, len(cleaned) + 80):
        return False

    original_tokens = cleaned.split()
    if not original_tokens:
        return True

    candidate_lower = candidate.casefold()
    hits = sum(1 for token in original_tokens if token.casefold() in candidate_lower)
    if hits < max(1, int(len(original_tokens) * 0.7)):
        return False

    lead = original_tokens[0].casefold()
    if lead and lead not in candidate_lower[: max(len(lead) * 3, 40)]:
        return False

    return True


def _recover_with_ocr_text(text: str, ocr_text: str) -> str:
    """Apply general OCR recovery strategies to one string."""
    if not ocr_text:
        return text

    repaired = fill_placeholders_from_ocr(text, ocr_text)
    repaired = _normalize_numeric_spacing(repaired)
    if not text_needs_ocr_repair(repaired):
        return repaired

    if _ocr_is_better(text, ocr_text):
        return _normalize_numeric_spacing(ocr_text)

    return repaired


def repair_text_with_ocr(
    text: str,
    pdf_path: Path | str,
    page_no: int,
    bbox: BoundingBox | None,
) -> str:
    """
    Recover missing glyphs for arbitrary PDFs.

    Order matters:
    1. OCR-fill placeholders (digits, versions, names — anything the font dropped)
    2. Then repair remaining single-letter fi/fl ligatures
    3. Fall back to page OCR / full OCR replace if needed
    """
    if not text_needs_ocr_repair(text):
        return _normalize_numeric_spacing(text)

    repaired = text
    if bbox is not None:
        # Layout models can return boxes that clip ascenders/descenders by a few
        # points. Retry progressively wider crops only when placeholders remain.
        # The larger scale is reserved for the final retry to limit OCR cost.
        retry_options = (
            (3.0, 3.0),
            (3.0, max(8.0, abs(bbox.t - bbox.b) * 0.75)),
            (4.0, max(14.0, abs(bbox.t - bbox.b) * 1.25)),
        )
        for scale, pad in retry_options:
            ocr_text = ocr_bbox_region(
                pdf_path,
                page_no,
                bbox,
                scale=scale,
                pad=pad,
            )
            candidate = _recover_with_ocr_text(text, ocr_text)
            if _placeholder_run_len(candidate) < _placeholder_run_len(repaired):
                repaired = candidate
            if not text_needs_ocr_repair(repaired):
                break

    if text_needs_ocr_repair(repaired):
        page_ocr = ocr_page_text(pdf_path, page_no)
        page_repaired = _recover_with_ocr_text(text, page_ocr)
        if not text_needs_ocr_repair(page_repaired) or (
            _placeholder_run_len(page_repaired) < _placeholder_run_len(repaired)
        ):
            repaired = page_repaired

    # Ligatures only after numeric/glyph recovery, and only for single gaps.
    repaired = _repair_fi_ligatures(repaired)
    return _normalize_numeric_spacing(repaired)


def _page_no_for_table(doc: DoclingDocument, table) -> int | None:
    if not table.prov:
        return None
    return table.prov[0].page_no


def repair_missing_glyphs_with_ocr(doc: DoclingDocument, pdf_path: Path | str) -> None:
    """Re-read regions that contain missing-glyph placeholders using targeted OCR."""
    _PAGE_OCR_CACHE.clear()
    _BBOX_OCR_CACHE.clear()
    for item, _level in doc.iterate_items():
        if not isinstance(item, TextItem) or not text_needs_ocr_repair(item.text):
            continue
        if not item.prov:
            continue
        prov = item.prov[0]
        item.text = repair_text_with_ocr(item.text, pdf_path, prov.page_no, prov.bbox)
        if text_needs_ocr_repair(item.orig):
            item.orig = repair_text_with_ocr(item.orig, pdf_path, prov.page_no, prov.bbox)

    for table in doc.tables:
        page_no = _page_no_for_table(doc, table)
        if page_no is None:
            continue
        for cell in table.data.table_cells:
            if not isinstance(cell, TableCell) or not text_needs_ocr_repair(cell.text):
                continue
            cell.text = repair_text_with_ocr(cell.text, pdf_path, page_no, cell.bbox)
