import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class ModelConfig(BaseModel):
    name: str = Field(min_length=1)
    api_key: str = Field(alias="apikey", min_length=1)
    url: str = Field(min_length=1)
    compatible: str = "anthropic"


class AgentConfig(BaseModel):
    models: list[ModelConfig] = Field(min_length=1)
    skills_path: Path | None = None

    @model_validator(mode="after")
    def validate_unique_model_names(self) -> "AgentConfig":
        names = [model.name for model in self.models]
        if len(names) != len(set(names)):
            raise ValueError("模型名称不能重复")
        return self


class Settings(BaseSettings):
    APP_NAME: str = "Local Agent"
    CONFIG_PATH: Path = Path("~/.simple_agent/config.json")
    SYSTEM_PROMPT_PATH: Path | None = None
    DATA_DIR: Path

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_agent_config() -> AgentConfig:
    config_path = get_settings().CONFIG_PATH.expanduser()
    content = json.loads(config_path.read_text(encoding="utf-8"))
    return AgentConfig.model_validate(content)


def get_model_config(name: str | None = None) -> ModelConfig:
    models = get_agent_config().models
    if name is None:
        return models[0]
    for model in models:
        if model.name == name:
            return model
    raise ValueError(f"未知模型: {name}")
