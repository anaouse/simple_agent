from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Local Agent"
    ANTHROPIC_URL: str
    API_KEY: str
    ANTHROPIC_MODEL: str
    SYSTEM_PROMPT_PATH: Path | None = None

    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
