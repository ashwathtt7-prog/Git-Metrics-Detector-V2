from __future__ import annotations

import asyncio
from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    name = "Gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    def _get_client(self):
        from google import genai
        return genai.Client(api_key=self.api_key)

    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        from google.genai import types

        client = self._get_client()

        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text
