from dataclasses import dataclass


@dataclass(frozen=True)
class PromptGuardVerdict:
    malicious: bool
    label: str
    score: float | None = None
    failed_open: bool = False


@dataclass(frozen=True)
class DocumentShieldVerdict:
    attack_detected: list[bool]
    user_prompt_attack: bool = False
    failed_open: bool = False
