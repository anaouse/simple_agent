# 配置文件说明

配置文件位置：`~/.simple_agent/config.json`

## 配置格式

```json
{
  "models": [
    {
      "name": "claude-3-5-sonnet",
      "apikey": "your-anthropic-api-key",
      "url": "https://api.anthropic.com",
      "compatible": "anthropic"
    },
    {
      "name": "gpt-4o",
      "apikey": "your-openai-api-key",
      "url": "https://api.openai.com/v1",
      "compatible": "openai"
    }
  ],
  "skills_path": "~/.simple_agent/skills"
}
```

## 字段说明

- `name`: 模型名称，会显示在前端的模型选择列表中
- `apikey`: 模型 API 的密钥
- `url`: API 的基础 URL
  - Anthropic: `https://api.anthropic.com`
  - OpenAI: `https://api.openai.com/v1`
  - 其他兼容 OpenAI 格式的服务（如 Azure OpenAI、本地部署等）也使用 `openai` compatible
- `compatible`: API 格式类型
  - `anthropic`: 使用 Anthropic 的 API 格式
  - `openai`: 使用 OpenAI 的 API 格式
- `skills_path`: 可选，存放 skill 文件夹的路径。其第一层子文件夹中直接包含 `SKILL.md` 时，该文件夹会作为一个 skill 显示在 `/skill` 候选列表中。

## 支持的格式

### Anthropic 格式
适用于 Claude 系列模型。

### OpenAI 格式
适用于：
- OpenAI 官方模型（GPT-4、GPT-3.5 等）
- Azure OpenAI
- 其他兼容 OpenAI API 格式的服务

## 切换模型

在前端使用 `/model` 命令可以切换当前使用的模型。系统会根据模型配置中的 `compatible` 字段自动选择对应的 Agent 实现。

## 注意事项

1. 配置文件中至少需要配置一个模型
2. 模型名称不能重复
3. 如果未指定模型，系统会使用配置文件中的第一个模型
4. 同一个会话中的所有消息格式会被自动转换，因此可以在不同模型之间切换继续对话
