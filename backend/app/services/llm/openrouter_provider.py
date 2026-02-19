from __future__ import annotations

import logging

import httpx

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class OpenRouterProvider(LLMProvider):
    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name="openrouter-llama-3.3-70b",
            max_context_tokens=100_000,
            supports_json_mode=False,
        )

    def is_available(self) -> bool:
        return bool(settings.openrouter_api_key)

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a JSON-only assistant. Respond with valid JSON only, no markdown, no explanation.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
