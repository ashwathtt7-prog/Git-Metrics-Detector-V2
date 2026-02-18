from __future__ import annotations

import asyncio
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider (GPT-4o, GPT-4o-mini, etc.)."""

    name = "OpenAI"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await asyncio.to_thread(
            client.chat.completions.create,
            **kwargs,
        )
        return response.choices[0].message.content
