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
        self.model = settings.gemini_model or "gemini-2.0-flash"

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
        # If a service account file is configured, require it to resolve. This prevents
        # silently falling back to API-key mode when the user expects Vertex auth.
        if settings.gemini_service_account_file:
            return bool(self._get_service_account_path())
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
        target_model = model_override or self.model

        lower = (prompt or "").lower()
        wants_json = ("```json" in lower) or ("respond as json" in lower) or ("respond in json" in lower) or ("valid json" in lower)

        # Minimize safety filters to prevent blocking on source code analysis
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
        ]

        # Vertex/Gemini can occasionally return an empty `response.text` for transient reasons.
        # We retry a couple of times, re-initializing the client and lowering output tokens.
        max_tokens_by_attempt = [8192, 4096, 2048]
        last_err: Exception | None = None

        for attempt in range(len(max_tokens_by_attempt)):
            client = self._get_client()
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens_by_attempt[attempt],
                        safety_settings=safety_settings,
                        **({"response_mime_type": "application/json"} if wants_json else {}),
                    ),
                )

                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    # Fallback: some SDK versions may not populate `response.text` reliably.
                    try:
                        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                            parts = response.candidates[0].content.parts
                            joined = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", "")])
                            text = (joined or "").strip()
                    except Exception:
                        pass

                if not text:
                    finish_reason = "unknown"
                    safety = None
                    try:
                        if response.candidates:
                            cand = response.candidates[0]
                            finish_reason = str(getattr(cand, "finish_reason", "unknown"))
                            safety = getattr(cand, "safety_ratings", None)
                    except Exception:
                        pass
                    raise ValueError(
                        f"Gemini empty response (finish_reason={finish_reason}, "
                        f"model={target_model}, prompt_chars={len(prompt)}, safety={safety})"
                    )

                return text
            except Exception as e:
                last_err = e
                # Force re-init on subsequent attempt.
                self._client = None
                if attempt < len(max_tokens_by_attempt) - 1:
                    logger.warning(
                        f"[Gemini] Attempt {attempt+1}/{len(max_tokens_by_attempt)} failed ({type(e).__name__}); "
                        f"retrying with max_output_tokens={max_tokens_by_attempt[attempt+1]}..."
                    )
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                break

        assert last_err is not None
        if isinstance(last_err, ValueError):
            raise last_err
        logger.error(f"Gemini generation failed: {last_err}")
        raise last_err
