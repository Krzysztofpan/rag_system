from app.services.security.types import DocumentShieldVerdict, PromptGuardVerdict


def should_block_user_prompt(
    verdict: PromptGuardVerdict,
    *,
    threshold: float,
) -> bool:
    if verdict.failed_open or verdict.score is None:
        return False
    return verdict.score >= threshold


def should_block_shielded_user_prompt(verdict: DocumentShieldVerdict) -> bool:
    return not verdict.failed_open and verdict.user_prompt_attack


def kept_document_indexes(verdict: DocumentShieldVerdict) -> list[int]:
    if verdict.failed_open:
        return list(range(len(verdict.attack_detected)))
    return [
        index
        for index, attacked in enumerate(verdict.attack_detected)
        if not attacked
    ]
