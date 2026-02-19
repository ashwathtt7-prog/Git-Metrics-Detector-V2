from __future__ import annotations

import logging

import httpx

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

MODEL = "llama3.1:8b"


class OllamaProvider(LLMProvider):
    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name="ollama-llama-3.1-8b",
            max_context_tokens=100_000,
            supports_json_mode=True,
        )

    def is_available(self) -> bool:
        return bool(settings.ollama_base_url)

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        base_url = settings.ollama_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
