from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM provider selection: ollama, gemini, openai, anthropic
    llm_provider: str = "ollama"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Ollama (local — no API key needed)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # GitHub
    github_token: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/metrics.db"

    # Apache Superset
    superset_url: str = "http://localhost:8088"
    superset_username: str = "admin"
    superset_password: str = "admin"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
