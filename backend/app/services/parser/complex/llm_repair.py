from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable

from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table_data import TableCell
from docling_core.types.doc.items.text import TextItem

from app.config import get_settings

from .ocr_repair import text_needs_ocr_repair

logger = logging.getLogger(__name__)

BATCH_SIZE = 8

SYSTEM_PROMPT = """You repair text extracted from PDF documents.

Fix ONLY extraction / OCR defects. Do not change meaning or add content.

Spacing (important — fix these aggressively when clearly wrong):
- Missing spaces between words: "frameworkforidentifying" → "framework for identifying", "Createorextend" → "Create or extend", "Acyber" → "A cyber"
- Spurious spaces inside a single word (often broken fi/fl ligatures): "Arti ficial" → "Artificial", "ef ficiently" → "efficiently", "speci fic" → "specific"
- Glued phrases at word boundaries: "yourfingertips" → "your fingertips"

Other defects to fix:
- Broken ligatures left as partial letters
- Obvious OCR typos (e.g. "Juypter" → "Jupyter") when unambiguous
- Broken table-cell text from layout/parsing (split/merged words)

Do NOT:
- Summarize, translate, rephrase for style, or invent missing facts
- Invent, guess, or "restore" numbers, years, versions, IDs, or codes
- Change correct punctuation, numbers, product names, or markdown/table structure
- "Normalize" ATT&CK / ATLAS / OWASP names beyond fixing clear extraction errors
- Replace missing-digit gaps with words (never turn a year/number hole into "first", "Act I", "spon", etc.)

Return JSON only: {"repairs": [{"id": <int>, "text": "<fixed text>"}, ...]}
Include exactly one entry for every id you received. If a fragment needs no change, return it unchanged.
"""


@dataclass
class _RepairTarget:
    id: int
    text: str
    setter: Callable[[str], None]


def _needs_llm_repair(text: str) -> bool:
    # Leave unresolved missing glyphs to OCR — LLM tends to invent numbers/words.
    if text_needs_ocr_repair(text):
        return False
    return len(text.strip()) >= 4 and bool(re.search(r"[^\W\d_]", text, re.UNICODE))


_NUMBER_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand)\b",
    re.I,
)


def _llm_fix_is_safe(original: str, fixed: str) -> bool:
    """Reject LLM edits that invent numbers or drop existing ones."""
    if not fixed.strip():
        return False
    if text_needs_ocr_repair(fixed):
        return False
    orig_digits = re.findall(r"\d+", original)
    fixed_digits = re.findall(r"\d+", fixed)
    if fixed_digits != orig_digits:
        return False

    original_letters = re.sub(r"[^\w]", "", original, flags=re.UNICODE).casefold()
    for match in _NUMBER_WORDS.finditer(fixed):
        if match.group(0).casefold() not in original_letters:
            return False

    protected = re.compile(r"(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.\w+", re.I)
    if protected.findall(original) != protected.findall(fixed):
        return False

    original_norm = " ".join(original.split())
    fixed_norm = " ".join(fixed.split())
    if len(fixed_norm) > max(len(original_norm) * 1.25, len(original_norm) + 20):
        return False
    if SequenceMatcher(None, original_norm.casefold(), fixed_norm.casefold()).ratio() < 0.72:
        return False
    return True


def _collect_targets(doc: DoclingDocument) -> list[_RepairTarget]:
    targets: list[_RepairTarget] = []
    counter = 0

    def add(text: str, setter) -> None:
        nonlocal counter
        if not text.strip() or not _needs_llm_repair(text):
            return
        targets.append(_RepairTarget(id=counter, text=text, setter=setter))
        counter += 1

    for item, _level in doc.iterate_items():
        if isinstance(item, TextItem):
            add(item.text, lambda value, item=item: setattr(item, "text", value))
            if item.orig != item.text:
                add(item.orig, lambda value, item=item: setattr(item, "orig", value))

    for table in doc.tables:
        for cell in table.data.table_cells:
            if isinstance(cell, TableCell):
                add(cell.text, lambda value, cell=cell: setattr(cell, "text", value))

    return targets


def _call_llm(batch: list[_RepairTarget], model: str, api_key: str) -> dict[int, str]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    payload = [{"id": target.id, "text": target.text} for target in batch]
    llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Fix spacing and extraction defects in these fragments. "
                    "Especially restore missing spaces between words and remove "
                    "spurious spaces inside single words.\n"
                    + json.dumps(payload, ensure_ascii=False)
                )
            ),
        ]
    )
    content = response.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    data = json.loads(content)
    return {entry["id"]: entry["text"] for entry in data["repairs"]}


def repair_document_with_llm(
    doc: DoclingDocument,
    *,
    model: str | None = None,
    enabled: bool = True,
) -> DoclingDocument:
    if not enabled:
        return doc

    settings = get_settings()
    if not settings.openai_api_key:
        logger.info("LLM repair skipped: openai_api_key not set")
        return doc

    resolved_model = model or settings.parser_llm_model
    targets = _collect_targets(doc)
    if not targets:
        return doc

    for start in range(0, len(targets), BATCH_SIZE):
        batch = targets[start : start + BATCH_SIZE]
        try:
            fixes = _call_llm(batch, resolved_model, settings.openai_api_key)
        except Exception as exc:
            logger.warning("LLM repair batch failed: %s", exc)
            continue
        for target in batch:
            fixed = fixes.get(target.id)
            if fixed and _llm_fix_is_safe(target.text, fixed):
                target.setter(fixed)

    return doc
