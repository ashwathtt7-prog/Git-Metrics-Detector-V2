from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM provider selection: ollama, gemini, openai, anthropic
    llm_provider: str = "ollama"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
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

    # Metabase
    metabase_url: str = "http://localhost:3003"
    metabase_username: str = ""
    metabase_password: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" # Ignore extra env vars

settings = Settings()
print(f"[Config] Loaded settings. Provider: {settings.llm_provider}")
print(f"[Config] Gemini Service Account: {settings.gemini_service_account_file}")
print(f"[Config] Gemini API Key present: {bool(settings.gemini_api_key)}")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
