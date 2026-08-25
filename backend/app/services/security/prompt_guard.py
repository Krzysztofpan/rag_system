from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from uuid import UUID

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

from app.lib.prompt_guard_tokenizer import get_prompt_guard_tokenizer
from app.lib.tracing import conversation_tracing
from app.services.security.policies import should_block_user_prompt
from app.services.security.types import PromptGuardVerdict

logger = logging.getLogger(__name__)


class PromptGuardService:
    def __init__(
        self,
        *,
        model: str,
        threshold: float,
        enabled: bool,
        fail_open: bool,
        max_prompt_tokens: int,
        groq_llm: ChatOpenAI | None = None,
    ) -> None:
        self._model = model
        self._threshold = threshold
        self._enabled = enabled
        self._fail_open = fail_open
        self._max_prompt_tokens = max_prompt_tokens
        self._groq_llm = groq_llm

    async def should_block_message(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
        text: str,
    ) -> bool:
        with conversation_tracing(
            conversation_id,
            user_id=user_id,
            tags=["security", "prompt_guard"],
        ):
            verdict = await self.classify(text)
        return should_block_user_prompt(verdict, threshold=self._threshold)

    async def classify_messages(self, texts: list[str]) -> PromptGuardVerdict:
        non_empty = [text for text in texts if text.strip()]
        if not non_empty:
            return PromptGuardVerdict(malicious=False, label="benign")
        verdicts = list(await asyncio.gather(
            *(self.classify(text) for text in non_empty)
        ))
        return self._worst_verdict(verdicts)

    async def classify(self, text: str) -> PromptGuardVerdict:
        if not self._enabled:
            return PromptGuardVerdict(malicious=False, label="disabled")
        if self._groq_llm is None:
            logger.warning("Prompt Guard skipped: GROQ_API_KEY is not configured")
            return PromptGuardVerdict(
                malicious=False,
                label="unavailable",
                failed_open=True,
            )

        try:
            verdicts = list(await asyncio.gather(
                *(self._score_text(window) for window in self._token_windows(text))
            ))
        except Exception:
            logger.exception("Prompt Guard request failed")
            if self._fail_open:
                return PromptGuardVerdict(
                    malicious=False,
                    label="error",
                    failed_open=True,
                )
            raise

        return self._worst_verdict(verdicts)

    async def _score_text(self, text: str) -> PromptGuardVerdict:
        if self._groq_llm is None:
            raise RuntimeError("Prompt Guard client is not configured")
        response = await self._groq_llm.ainvoke(text)
        return self._parse_response(response)

    def _parse_response(self, response: BaseMessage) -> PromptGuardVerdict:
        content = response.content if isinstance(response.content, str) else ""
        try:
            score = float(content.strip())
        except ValueError:
            if self._fail_open:
                return PromptGuardVerdict(
                    malicious=False,
                    label="invalid",
                    failed_open=True,
                )
            raise
        malicious = score >= self._threshold
        return PromptGuardVerdict(
            malicious=malicious,
            label="malicious" if malicious else "benign",
            score=score,
        )

    def _token_windows(self, text: str) -> list[str]:
        tokenizer = get_prompt_guard_tokenizer()
        special = tokenizer.num_special_tokens_to_add(pair=False)
        size = max(self._max_prompt_tokens - special, 1)
        token_ids = tokenizer.encode(text, add_special_tokens=False)
        if len(token_ids) <= size:
            return [text]
        return [
            tokenizer.decode(token_ids[start : start + size], skip_special_tokens=True)
            for start in range(0, len(token_ids), size)
        ]

    @staticmethod
    def _worst_verdict(verdicts: list[PromptGuardVerdict]) -> PromptGuardVerdict:
        if not verdicts:
            return PromptGuardVerdict(malicious=False, label="benign")
        if all(verdict.failed_open for verdict in verdicts):
            return verdicts[0]
        blocking = [verdict for verdict in verdicts if verdict.malicious]
        if not blocking:
            return next(
                (verdict for verdict in verdicts if not verdict.failed_open),
                verdicts[0],
            )
        return max(blocking, key=lambda verdict: verdict.score or 1.0)


@lru_cache
def get_prompt_guard_service() -> PromptGuardService:
    settings = get_settings()
    groq_llm = ChatOpenAI(
        model=settings.prompt_guard_model, 
        base_url=settings.prompt_guard_base_url,
        api_key=settings.groq_api_key
    )
    return PromptGuardService(
        model=settings.prompt_guard_model,
        threshold=settings.prompt_guard_threshold,
        enabled=settings.prompt_guard_enabled,
        fail_open=settings.prompt_guard_fail_open,
        max_prompt_tokens=settings.prompt_guard_max_prompt_tokens,
        groq_llm=groq_llm,
    )
