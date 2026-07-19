# OpenAI 格式支持实现总结

## 新增文件

### 1. `backend/app/ai/openai_agent.py`
实现了支持 OpenAI 格式 API 的 Agent，核心功能：
- 使用 `AsyncOpenAI` 客户端与 OpenAI API 通信
- 处理流式响应，收集 content delta 和 tool calls
- 将 Anthropic 风格的工具定义转换为 OpenAI function calling 格式
- 执行工具调用并返回结果
- 支持工具错误检测

### 2. `backend/app/ai/openai_adaptor.py`
处理 OpenAI 流式响应的适配器：
- 从流式响应中提取文本增量
- 简化了 OpenAI API 返回的复杂结构

### 3. `backend/app/ai/openai_session_adaptor.py`
实现 OpenAI 消息格式与本项目事件格式的双向转换：
- `to_openai()`: 将项目消息格式转换为 OpenAI 对话格式
- `from_openai()`: 将 OpenAI 对话格式转换回项目消息格式
- 处理 assistant 消息、tool calls 和 tool results 的正确组织

### 4. `docs/config_example.md`
配置文件说明文档：
- 解释了 `compatible` 字段的作用
- 提供了 Anthropic 和 OpenAI 格式的配置示例
- 说明了如何切换模型

## 修改文件

### `backend/app/main.py`
1. 导入 `OpenAIAgent`
2. 修改模型验证逻辑，支持 `anthropic` 和 `openai` 两种格式
3. 根据 `model_config.compatible` 字段动态创建对应的 Agent

```python
if model_config.compatible == "openai":
    agent = OpenAIAgent(SETTINGS, model_config, resolved)
else:
    agent = AnthropicAgent(SETTINGS, model_config, resolved)
```

## 功能特性

### 统一的事件协议
无论使用 Anthropic 还是 OpenAI 模型，都会发送相同的事件：
- `content_delta`: 文本增量
- `tool_call_start`: 工具调用开始
- `tool_call_result`: 工具调用结果

### 会话格式转换
同一段聊天记录可以在不同格式的模型之间切换：
- 从 Anthropic 切换到 OpenAI：`AnthropicSessionAdaptor.to_anthropic()` 加载会话 → 继续对话 → `OpenAISessionAdaptor.to_openai()` 发送给新模型
- 所有消息都存储为统一的 `ChatMessage` 格式

### 工具调用兼容性
- Anthropic 格式：`tool_use` block with `input_schema`
- OpenAI 格式：`function` calling with `parameters`
- 项目的工具定义使用 JSON Schema，可以直接用于两种格式

## 使用方法

1. 在 `~/.simple_agent/config.json` 中添加 OpenAI 格式的模型：
```json
{
  "models": [
    {
      "name": "gpt-4o",
      "apikey": "sk-...",
      "url": "https://api.openai.com/v1",
      "compatible": "openai"
    }
  ]
}
```

2. 前端使用 `/model` 命令切换到该模型

3. 后端会自动选择 `OpenAIAgent` 处理请求

## 注意事项

1. OpenAI 的 system prompt 作为第一条消息发送，而不是单独的 system 参数
2. 工具调用的 arguments 在 OpenAI 中是 JSON 字符串，需要序列化/反序列化
3. OpenAI 的流式响应中，tool calls 是增量式累积的，需要完整收集后才能使用
4. 两种格式的会话历史可以互相转换，但某些特定字段（如 Anthropic 的 thinking）可能丢失
