from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    ollama_base_url: str = ""
    github_token: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/metrics.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
