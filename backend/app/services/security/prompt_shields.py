from __future__ import annotations

import logging
from functools import lru_cache

import httpx

from app.config import get_settings
from app.services.security.errors import PromptAttackError
from app.services.security.policies import should_block_shielded_user_prompt
from app.services.security.types import DocumentShieldVerdict

logger = logging.getLogger(__name__)


class PromptShieldsService:
    def __init__(
        self,
        *,
        endpoint: str | None,
        api_key: str | None,
        enabled: bool,
        fail_open: bool,
        timeout_sec: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._endpoint = (endpoint or "").rstrip("/")
        self._api_key = api_key
        self._enabled = enabled
        self._fail_open = fail_open
        self._timeout_sec = timeout_sec
        self._api_version = settings.prompt_shields_api_version
        self._max_documents = settings.prompt_shields_max_documents
        self._max_document_chars = settings.prompt_shields_max_document_chars
        self._max_prompt_chars = settings.prompt_shields_max_prompt_chars
        self._http_client = http_client

    async def analyze(
        self,
        user_prompt: str,
        documents: list[str],
    ) -> DocumentShieldVerdict:
        if not documents:
            return DocumentShieldVerdict(attack_detected=[])
        if not self._enabled:
            return DocumentShieldVerdict(
                attack_detected=[False] * len(documents),
            )
        if not self._endpoint or not self._api_key:
            logger.warning("Prompt Shields skipped: Azure Content Safety is not configured")
            return DocumentShieldVerdict(
                attack_detected=[False] * len(documents),
                failed_open=True,
            )

        batches = self.batch_documents(documents)
        flags = [False] * len(documents)
        user_prompt_attack = False

        try:
            for start, batch in batches:
                payload = await self._request(user_prompt, batch)
                user_prompt_attack = user_prompt_attack or bool(
                    (payload.get("userPromptAnalysis") or {}).get("attackDetected")
                )
                analyses = payload.get("documentsAnalysis") or []
                for offset, analysis in enumerate(analyses):
                    index = start + offset
                    if index >= len(flags):
                        break
                    if isinstance(analysis, dict) and analysis.get("attackDetected"):
                        flags[index] = True
        except Exception:
            logger.exception("Prompt Shields request failed")
            if self._fail_open:
                return DocumentShieldVerdict(
                    attack_detected=[False] * len(documents),
                    failed_open=True,
                )
            raise

        if user_prompt_attack:
            logger.info("Prompt Shields flagged userPromptAnalysis")

        verdict = DocumentShieldVerdict(
            attack_detected=flags,
            user_prompt_attack=user_prompt_attack,
        )
        if should_block_shielded_user_prompt(verdict):
            raise PromptAttackError()
        return verdict

    async def _request(self, user_prompt: str, documents: list[str]) -> dict:
        url = (
            f"{self._endpoint}/contentsafety/text:shieldPrompt"
            f"?api-version={self._api_version}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key or "",
            "Content-Type": "application/json",
        }
        body = {
            "userPrompt": user_prompt[: self._max_prompt_chars],
            "documents": documents,
        }
        if self._http_client is not None:
            response = await self._http_client.post(
                url,
                headers=headers,
                json=body,
                timeout=self._timeout_sec,
            )
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

    def batch_documents(self, documents: list[str]) -> list[tuple[int, list[str]]]:
        batches: list[tuple[int, list[str]]] = []
        current: list[str] = []
        current_chars = 0
        start = 0

        for index, document in enumerate(documents):
            text = document[: self._max_document_chars]
            if current and (
                len(current) >= self._max_documents
                or current_chars + len(text) > self._max_document_chars
            ):
                batches.append((start, current))
                current = []
                current_chars = 0
                start = index
            current.append(text)
            current_chars += len(text)

        if current:
            batches.append((start, current))
        return batches


@lru_cache
def get_prompt_shields_service() -> PromptShieldsService:
    settings = get_settings()
    return PromptShieldsService(
        endpoint=settings.azure_content_safety_endpoint,
        api_key=settings.azure_content_safety_key,
        enabled=settings.prompt_shields_enabled,
        fail_open=settings.prompt_shields_fail_open,
        timeout_sec=settings.prompt_shields_timeout_sec,
    )
