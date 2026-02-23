from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM provider selection: ollama, gemini, openai, anthropic
    llm_provider: str = "ollama"

    # Gemini
    gemini_api_key: str = ""
    # Default to a widely-available Vertex model name unless overridden via GEMINI_MODEL.
    gemini_model: str = "gemini-2.0-flash"
    gemini_service_account_file: str = ""

    # Ollama (local — no API key needed)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Groq
    groq_api_key: str = ""

    # OpenRouter
    openrouter_api_key: str = ""

    # GitHub
    github_token: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/metrics.db"

    # LLM prompt shaping / safety limits
    # (Large files can cause provider timeouts/empty responses on some models.)
    llm_max_file_chars: int = 6000

    # Metabase
    metabase_url: str = "http://localhost:3003"
    metabase_username: str = ""
    metabase_password: str = ""

    class Config:
        # Always load the backend-local env file, regardless of where the process is started from.
        # This avoids confusing partial configuration (e.g., LLM auth loaded but Metabase creds missing)
        # when running `uvicorn` from a different working directory.
        env_file = str((Path(__file__).resolve().parent.parent / ".env"))
        env_file_encoding = "utf-8"
        extra = "ignore" # Ignore extra env vars

settings = Settings()
print(f"[Config] Loaded settings. Provider: {settings.llm_provider}")
print(f"[Config] Gemini Service Account: {settings.gemini_service_account_file}")
print(f"[Config] Gemini API Key present: {bool(settings.gemini_api_key)}")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
