from __future__ import annotations

import asyncio
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    name = "Anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)

        system_msg = "You are an expert software analyst. Always respond with valid JSON." if json_mode else ""

        response = await asyncio.to_thread(
            client.messages.create,
            model=self.model,
            max_tokens=4096,
            temperature=0.1,
            system=system_msg,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
