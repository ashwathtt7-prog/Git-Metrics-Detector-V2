from __future__ import annotations

import asyncio
import logging
import os
import json

from google import genai
from google.genai import types
from google.oauth2 import service_account

from ...config import settings
from .base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

# Primary scopes for Service Account
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]


class GeminiProvider(LLMProvider):
    def __init__(self):
        self._client = None
        self.model = settings.gemini_model or "gemini-2.5-flash"

    def config(self) -> ProviderConfig:
        return ProviderConfig(
            name=self.model,
            max_context_tokens=32_000,
            supports_json_mode=True,
            rpm_limit=5,
            rpd_limit=25,
        )

    def _get_service_account_path(self) -> str | None:
        """Resolve the service account file path."""
        sa_file = settings.gemini_service_account_file
        if not sa_file:
            return None
        
        # 1. Check if it's already an absolute path
        if os.path.isabs(sa_file) and os.path.isfile(sa_file):
            return sa_file
            
        # 2. Check relative to CWD (usually backend/)
        if os.path.isfile(sa_file):
            return os.path.abspath(sa_file)
            
        # 3. Check relative to backend/ directory (3 levels up from this file)
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        candidate = os.path.join(backend_dir, sa_file)
        if os.path.isfile(candidate):
            return candidate
            
        return None

    def is_available(self) -> bool:
        return bool(settings.gemini_api_key) or bool(self._get_service_account_path())

    def _get_client(self) -> genai.Client:
        if self._client:
            return self._client
            
        sa_path = self._get_service_account_path()
        if sa_path:
            # Load project ID from JSON
            try:
                with open(sa_path, "r") as f:
                    creds_data = json.load(f)
                    project_id = creds_data.get("project_id")
                
                if not project_id:
                    raise ValueError(f"Project ID not found in {sa_path}")
                
                credentials = service_account.Credentials.from_service_account_file(
                    sa_path, scopes=SCOPES
                )
                
                print(f"[GeminiProvider] Initializing for Vertex AI (Project: {project_id}) using {sa_path}")
                self._client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location="us-central1",
                    credentials=credentials
                )
                return self._client
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI client: {e}")
                raise ValueError(f"Gemini Vertex AI Init failed: {e}")
        
        elif settings.gemini_api_key:
            print("[GeminiProvider] Initializing for AI Studio using API Key")
            self._client = genai.Client(api_key=settings.gemini_api_key)
            return self._client
        
        raise ValueError("No valid Gemini credentials found in settings")

    async def generate(self, prompt: str, temperature: float = 0.1, model_override: str | None = None) -> str:
        client = self._get_client()
        target_model = model_override or self.model
        
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                ),
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            # Reset client on failure just in case it's a transient auth state issue
            self._client = None
            raise
