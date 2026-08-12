---
created_at: 2026-08-13T00:27:46+08:00
status: todo # done | todo
---

# 状况描述

agent使用edit命令的时候有时候会返回给前端：

```json
{
  "id": "call_00_SAwxSgR3gXonEFgQZMtN1963",
  "status": "error",
  "createdAt": "2026-08-12T16:19:16.993281Z",
  "role": "tool",
  "parentMessageId": "9571b10a-4bb4-40b4-9f27-3c88915623fa",
  "toolName": "edit",
  "arguments": {
    "_invalid_json": "Expecting value: line 1 column 70 (char 69)"
  },
  "result": "Error executing tool 'edit': edit() got an unexpected keyword argument '_invalid_json'"
}
```

看起来这个arguments意味着在调用的时候报错了返回了Exception，然后当作参数传递进去了。然后agent使用错误了几次之后就知道了如何传入数据，我这是在用AnthropicAgent时候遇到的错误

# 目的

调查清楚为什么会这样，给出修改方案，我同意后再修改

# 调查结论

## 直接原因（我们代码的问题）

`anthropic_agent.py` 在流式接收工具参数后统一解析：

```python
block["input"] = json.loads("".join(raw_json))
```

解析失败时，代码往参数里塞了一个伪造占位 key `_invalid_json`，随后在 `_execute_tools` 里被 `function(**tool_input)` 当真实关键字参数传给 `edit()`，产生二次错误：

```
edit() got an unexpected keyword argument '_invalid_json'
```

前端展示的 `arguments._invalid_json` 和那句误导性 result 都是这个占位逻辑制造的，不是上游真正返回的东西；它还会被持久化进会话历史，污染后续上下文。

## 根本原因（上游/兼容端点不守契约）

`json.loads` 失败发生在**上游流式转发阶段**：Anthropic 官方协议约定 `input_json_delta.partial_json` 各片段拼接起来必须是合法 JSON。但日志中错误从 7-31 反复出现到 8-13，几乎都集中在 `edit`（长多行字符串参数），错误形态有三类：

- `Expecting value: line 1 column N`（N≈63~101）→ JSON 不完整/被截断
- `Expecting ',' delimiter` → 结构错乱
- `Invalid control character at: line 1 column 295` → 字符串里出现未转义控制字符（换行）

使用的 Anthropic 兼容模型走的是第三方端点（`api.deepseek.com/anthropic`、`api.b.ai`），不是官方 Anthropic API。这些网关在流式转发工具参数时不严格遵守 `partial_json` 拼接契约，属于上游行为，代码里只能防御，无法根治。

## 为什么"用错几次就会了"

错误结果会被作为 `tool_result` 回传给模型，模型看到错误后重试，本质是"错误→重试"循环里碰巧试对了，不是学会正确格式。浪费 token、体验差。

# 修改方案（已确认）

1. 取消 `_invalid_json` 占位参数；解析失败时 `input` 置为 `{}`，错误信息按 `tool_use_id` 记入独立 dict `invalid_tool_inputs`（**不能塞进 block**，否则该字段会随 `assistant_message` 回传上游，被 Anthropic SDK 校验拒绝）
2. `_execute_tools` 对命中 `invalid_tool_inputs` 的调用跳过函数执行，直接返回 JSON 格式错误结果并标 `is_error=True`
3. 解析失败时日志打印完整原始拼接 JSON，便于排查上游
4. `openai_agent.py` 同样处理（它拿到的是整段 arguments 字符串，失败处理放在 `_execute_tools` 内）

# 修改过程

## `backend/app/ai/anthropic_agent.py`

- `reply()` 新增 `invalid_tool_inputs: dict[str, str] = {}`
- 解析失败分支改为：
  - 日志打印完整原始拼接 JSON（`raw arguments: {}`）
  - `block["input"] = {}`（不再有 `_invalid_json`）
  - `invalid_tool_inputs[str(block.get("id", ""))] = str(exception)`
- `_execute_tools` 增加 `invalid_tool_inputs` 参数，命中时返回：
  ```
  Error: tool 'edit' received invalid JSON arguments: Expecting value: line 1 column 70 (char 69)
  ```
  并跳过真实函数调用

## `backend/app/ai/openai_agent.py`

- 解析失败分支：日志打印完整原始 `arguments_str`，记录 `input_error`
- 执行时命中 `input_error` 跳过函数，直接返回 JSON 格式错误

# 效果

- 前端不再出现 `_invalid_json`，失败的工具节点展示明确的"JSON 在哪一列格式错误"信息，模型据此正确重试
- 日志保留完整原始 JSON，方便下次确认上游到底发了什么
- 无效参数不再传给工具函数，也不会污染会话历史
- `_invalid_json` 已从代码中完全移除

# 目前为止

以上修改只是让edit调用的时候错误可以写到日志而已，接下来应该查看日志然后看看具体是什么样。

