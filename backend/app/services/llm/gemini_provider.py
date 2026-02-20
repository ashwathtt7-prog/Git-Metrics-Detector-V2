from __future__ import annotations

import asyncio
import logging
import os

from google import genai
from google.genai import types
from google.oauth2 import service_account

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

SCOPES = [
    "https://www.googleapis.com/auth/generative-language",
    "https://www.googleapis.com/auth/cloud-platform",
]


class GeminiProvider(LLMProvider):
    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name="gemini-2.5-flash",
            max_context_tokens=800_000,
            supports_json_mode=True,
            rpm_limit=5,
            rpd_limit=25,
        )

    def _get_service_account_path(self) -> str | None:
        """Resolve the service account file path."""
        sa_file = settings.gemini_service_account_file
        if not sa_file:
            return None
        # Try absolute path first, then relative to backend/ dir
        if os.path.isabs(sa_file) and os.path.isfile(sa_file):
            return sa_file
        # Relative to backend/ directory
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        candidate = os.path.join(backend_dir, sa_file)
        if os.path.isfile(candidate):
            return candidate
        return None

    def is_available(self) -> bool:
        return bool(settings.gemini_api_key) or bool(self._get_service_account_path())

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        sa_path = self._get_service_account_path()
        if sa_path:
            credentials = service_account.Credentials.from_service_account_file(
                sa_path, scopes=SCOPES
            )
            client = genai.Client(credentials=credentials)
            logger.info("Using Gemini with service account credentials")
        else:
            client = genai.Client(api_key=settings.gemini_api_key)
            logger.info("Using Gemini with API key")

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
