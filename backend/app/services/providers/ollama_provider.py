from __future__ import annotations

import httpx
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider. No API key required."""

    name = "Ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            },
        }

        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["response"]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running (ollama serve) and model '{self.model}' is pulled (ollama pull {self.model})."
            )
