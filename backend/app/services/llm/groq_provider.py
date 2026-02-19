from __future__ import annotations

import asyncio
import logging

from groq import Groq

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"


class GroqProvider(LLMProvider):
    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name="groq-llama-3.3-70b",
            max_context_tokens=100_000,
            supports_json_mode=True,
            rpm_limit=30,
            rpd_limit=14400,
        )

    def is_available(self) -> bool:
        return bool(settings.groq_api_key)

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        client = Groq(api_key=settings.groq_api_key)
        
        # Groq requires "json" in the prompt when using response_format={"type": "json_object"}
        if "json" not in prompt.lower():
            prompt += "\n\nRespond in JSON."

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
