from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"


class GeminiProvider(LLMProvider):
    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name="gemini-2.5-flash",
            max_context_tokens=800_000,
            supports_json_mode=True,
            rpm_limit=5,
            rpd_limit=25,
        )

    def is_available(self) -> bool:
        return bool(settings.gemini_api_key)

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return response.text
