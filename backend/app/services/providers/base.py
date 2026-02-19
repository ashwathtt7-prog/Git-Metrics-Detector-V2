from __future__ import annotations

import abc
import asyncio
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_BASE_DELAY = 10  # seconds


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    name: str = "base"

    @abc.abstractmethod
    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        """Send a prompt and return the raw text response.

        Args:
            prompt: The prompt to send to the LLM.
            json_mode: If True, request JSON-formatted output from the model.

        Returns:
            Raw text response from the LLM.
        """
        ...

    async def generate_with_retry(self, prompt: str, json_mode: bool = True) -> str:
        """Call generate() with exponential-backoff retry on rate limits."""
        est_tokens = int(len(prompt) / 3.5)
        logger.info(f"[{self.name}] Calling LLM with ~{est_tokens} estimated input tokens")

        for attempt in range(MAX_RETRIES):
            try:
                result = await self.generate(prompt, json_mode=json_mode)
                logger.info(f"[{self.name}] Success on attempt {attempt + 1}")
                return result
            except Exception as e:
                error_str = str(e).lower()
                logger.warning(
                    f"[{self.name}] Error (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )

                is_rate_limit = any(
                    kw in error_str
                    for kw in ("429", "rate", "quota", "resource", "too many", "overloaded")
                )

                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info(f"[{self.name}] Rate limited, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError(f"[{self.name}] Max retries exceeded for LLM call")
