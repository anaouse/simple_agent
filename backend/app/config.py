import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

CONFIG_PATH = Path.home() / ".simple_agent" / "config.json"


class ModelConfig(BaseModel):
    name: str = Field(min_length=1)
    api_key: str = Field(alias="apikey", min_length=1)
    url: str = Field(min_length=1)
    compatible: str = "anthropic"


class AgentConfig(BaseModel):
    models: list[ModelConfig] = Field(min_length=1)
    system_prompt_path: Path | None = None
    data_dir: Path
    skills_path: Path | None = None

    @model_validator(mode="after")
    def validate_unique_model_names(self) -> "AgentConfig":
        names = [model.name for model in self.models]
        if len(names) != len(set(names)):
            raise ValueError("模型名称不能重复")
        return self


def get_agent_config() -> AgentConfig:
    config_path = CONFIG_PATH
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
