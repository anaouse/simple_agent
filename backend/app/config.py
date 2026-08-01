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
    default_model: str | None = None
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
    config = get_agent_config()
    models = config.models
    model_name = name if name is not None else config.default_model
    if model_name is None:
        return models[0]
    for model in models:
        if model.name == model_name:
            return model
    if name is None:
        return models[0]
    raise ValueError(f"未知模型: {name}")


def set_default_model(name: str) -> None:
    content = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = AgentConfig.model_validate(content)
    if not any(model.name == name for model in config.models):
        raise ValueError(f"未知模型: {name}")
    content["default_model"] = name
    CONFIG_PATH.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
