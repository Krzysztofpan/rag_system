LLM_REPAIR_SYSTEM_PROMPT = """You repair text extracted from PDF documents.

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

LLM_REPAIR_HUMAN_INSTRUCTIONS = (
    "Fix spacing and extraction defects in these fragments. "
    "Especially restore missing spaces between words and remove "
    "spurious spaces inside single words."
)


def llm_repair_human_message(payload_json: str) -> str:
    return f"{LLM_REPAIR_HUMAN_INSTRUCTIONS}\n{payload_json}"
