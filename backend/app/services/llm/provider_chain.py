from __future__ import annotations

import asyncio
import logging
from typing import List

from .base import LLMProvider

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_PROVIDER = 3
RATE_LIMIT_RETRY_DELAY = 5  # seconds


class LLMProviderChain:
    """Manages a fallback chain of LLM providers with sticky preference."""

    def __init__(self, providers: List[LLMProvider]):
        self._available = [p for p in providers if p.is_available()]
        self._preferred_index = 0
        if not self._available:
            raise RuntimeError(
                "No LLM providers available. Configure at least one of: "
                "GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or OLLAMA_BASE_URL"
            )
        logger.info(
            f"[LLM Chain] Available providers: "
            f"{[p.config().name for p in self._available]}"
        )

    def get_max_context_tokens(self) -> int:
        """Return the minimum context across all available providers."""
        return min(p.config().max_context_tokens for p in self._available)

    async def generate(self, prompt: str, temperature: float = 0.1, model_override: str | None = None) -> str:
        """Try providers in order starting from preferred. On failure, fall through."""
        errors = []
        n = len(self._available)

        for offset in range(n):
            idx = (self._preferred_index + offset) % n
            provider = self._available[idx]
            cfg = provider.config()

            for attempt in range(MAX_RETRIES_PER_PROVIDER):
                try:
                    est_tokens = int(len(prompt) / 3.0)
                    logger.info(
                        f"[LLM] Trying {cfg.name} "
                        f"(attempt {attempt + 1}/{MAX_RETRIES_PER_PROVIDER}, "
                        f"~{est_tokens} input tokens)"
                    )
                    result = await provider.generate(prompt, temperature, model_override=model_override)
                    self._preferred_index = idx
                    logger.info(f"[LLM] Success with {cfg.name}")
                    return result

                except Exception as e:
                    error_str = str(e).lower()
                    is_retriable = any(
                        kw in error_str
                        for kw in ["429", "rate", "quota", "resource", "limit", "empty response"]
                    )

                    logger.warning(
                        f"[LLM] {cfg.name} error "
                        f"(attempt {attempt + 1}): {type(e).__name__}: {str(e)[:200]}"
                    )
                    error_msg = str(e) or type(e).__name__
                    errors.append(f"{cfg.name}: {error_msg}")

                    if is_retriable and attempt < MAX_RETRIES_PER_PROVIDER - 1:
                        delay = min(RATE_LIMIT_RETRY_DELAY * (2 ** attempt), 60)
                        logger.info(
                            f"[LLM] Rate limited on {cfg.name}, waiting {delay}s"
                        )
                        await asyncio.sleep(delay)
                    elif is_retriable:
                        logger.info(
                            f"[LLM] {cfg.name} exhausted, trying next provider"
                        )
                        break
                    else:
                        # Non-rate-limit error, try next provider immediately
                        break

        if n == 1:
            raise RuntimeError(f"{self._available[0].config().name} failed. Errors: {'; '.join(errors)}")
        raise RuntimeError(f"All LLM providers failed. Errors: {'; '.join(errors)}")
