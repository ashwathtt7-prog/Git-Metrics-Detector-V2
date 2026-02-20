from __future__ import annotations

import asyncio
from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider.
    
    Supports both AI Studio (API Key) and Vertex AI (Service Account).
    """

    name = "Gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash", service_account_file: str = ""):
        from ...config import settings
        
        self.api_key = api_key or settings.gemini_api_key
        # Ensure we prioritize the specific model requested by user if set in env
        self.model = settings.gemini_model or model
        self.service_account_file = service_account_file or settings.gemini_service_account_file
        
        self._vertex_initialized = False
        self._client = None
        
        # Resolve service account file to absolute path if provided
        if self.service_account_file:
            import os
            if not os.path.isabs(self.service_account_file):
                # Assume relative to backend root (where main.py / .env usually is)
                # But we are in app/services/providers
                # Let's try to find it relative to CWD first
                if os.path.exists(self.service_account_file):
                    self.service_account_file = os.path.abspath(self.service_account_file)
                else:
                    # Try looking in parent dirs? Or just leave it and let vertexai fail
                    pass

        # Log which mode we are in
        if self.service_account_file:
            print(f"[GeminiProvider] Initialized in Vertex AI mode with service account: {self.service_account_file}")
        elif self.api_key and self.api_key.strip():
            print("[GeminiProvider] Initialized in AI Studio mode with API Key")
        else:
            print("[GeminiProvider] Warning: No credentials found")

    async def generate(self, prompt: str, json_mode: bool = True) -> str:
        # --- METHOD C: Unified GenAI SDK ---
        from google import genai
        from google.genai import types
        import asyncio

        if not self._client:
            if self.service_account_file:
                # VERTEX AI MODE
                from google.oauth2 import service_account
                import json

                # 1. Load Project ID
                try:
                    with open(self.service_account_file, "r") as f:
                        creds_data = json.load(f)
                        project_id = creds_data.get("project_id")
                    
                    if not project_id:
                        raise ValueError(f"Project ID not found in {self.service_account_file}")
                except Exception as e:
                    raise ValueError(f"Failed to read service account file: {e}")

                # 2. Load Credentials with Scope
                try:
                    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
                    credentials = service_account.Credentials.from_service_account_file(
                        self.service_account_file, 
                        scopes=scopes
                    )
                    print(f"[GeminiProvider] Loaded Credentials for Project: {project_id}")
                except Exception as e:
                    raise ValueError(f"Failed to load Service Account credentials: {e}")

                # 3. Initialize Client with Explicit Arguments
                print(f"[GeminiProvider] Initializing genai.Client(vertexai=True, project='{project_id}', location='us-central1')...")
                try:
                    # Explicitly passing all arguments as requested by the error message
                    self._client = genai.Client(
                        vertexai=True,
                        project=project_id,
                        location="us-central1",
                        credentials=credentials
                    )
                    print("[GeminiProvider] Client initialized successfully.")
                except Exception as init_err:
                    print(f"[GeminiProvider] Client init failed: {init_err}")
                    raise

            elif self.api_key and self.api_key.strip():
                # AI STUDIO MODE
                self._client = genai.Client(api_key=self.api_key)
                print("[GeminiProvider] Client initialized for AI Studio")
            
            else:
                raise ValueError("No valid credentials provided for Gemini (API Key or Service Account needed)")

        # Prepare configuration
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        # Execute generation
        try:
            # We use to_thread because standard client is sync
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            raise ValueError(f"Gemini generation failed: {e}")
            
        else:
            raise ValueError("No valid credentials provided for Gemini (API Key or Service Account needed)")

