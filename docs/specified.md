# 项目约定文档

这是一个本地极简ai agent的前后端项目，本文档为项目统一约定，会随着项目的发展加入更多约定，没有特殊理由请严格遵守，如需打破约定请先在此文档中更新说明。

开发的时候我使用热重载开发，所以不用编译验证，有错误的话我会告诉你的，尽可能只使用文件编辑工具即可，然后查找什么的使用grep，find的bash命令，

---

## 后端

- 使用 FastAPI，所有接口的请求 / 响应数据必须用 Pydantic Model 定义，不允许裸 dict 或 `Any`
- 服务端口固定为 `2453`
- 常规 REST 接口统一挂在 `/api/` 前缀下（如 `/api/sessions`、`/api/messages`），WebSocket 路径统一挂在 `/ws/` 前缀下，避免混在一起
- 错误统一走 FastAPI 全局异常处理器（`exception_handler`），返回统一结构，错误码使用大写加下划线
  ```json
  { "error": { "code": "TOOL_TIMEOUT", "message": "工具执行超时" } }
  ```
  业务代码里不要每个路由自己返回 `HTTPException` 然后各自拼 detail 格式
- 成功的请求直接返回扁平的json格式数据不包含 "error" 字段
- 环境变量，主要是base url以及api key我自己设置统一放 `.env`，格式你可以查看 `.env.example`，用 `pydantic-settings` 的 `BaseSettings` 加载，代码里不允许硬编码密钥 / 路径 / 上游 API 地址，写一个config.py文件提供一个函数，后端要用可以直接：
```
from config import get_settings
SETTINGS = get_settings()
print(SETTINGS.APP_NAME)
```
- 关键节点必须打日志：收到用户消息、调用上游 API 开始/结束、工具调用开始/结束、异常。用 `loguru`
- 放到app/文件夹当中，引用使用绝对路径引用，比如（from app.ai.anthropic_adaptor import AnthropicAdaptor）
- 使用watchfile监控当前项目下方文件变化

---

## 前端

- 使用 `@` 作为 `src/` 文件引用路径
- 不写 `useCallback` 和 `useMemo`，已启用 React Compiler 自动优化
- 跨文件引用的数据类型统一写到 `@/types.ts`
- 常规非流式请求（增删改查）用 axios，不要为了"统一"塞进 WebSocket 里
- 开发端口为 vite 默认的 `5173`
- 部署端口为 `5000`
- 组件化开发，尽可能写组件，然后在page文件当中进行组装，命名例子：InputBox.tsx
- 所有组件和page的css放到css文件夹下，命名和组件名称一样，但是形态变化，例子为：input-box.css， home-page.css
- @/root.css 放置本项目的颜色变量，所有css都需要使用root.css当中的颜色变量作为颜色，如果真的需要添加颜色也请加入到 root.css当中再调用
- 所有css都在 `main.tsx` 当中引入，不要在组件内部或者page当中引入，忽略tailwind.css虽然我安装了，但是组件的css自己写，不要用tailwind css
- 页面放到 pages 文件夹当中

---

## 实时通信设计（WebSocket）

### 什么时候用 WS，什么时候用 REST

- **WS**：agent 回复的流式输出、工具调用过程状态、需要服务端主动推送的场景
- **REST**：创建会话、获取历史消息列表等语义明确、需要幂等重试的操作

不要把所有请求都塞进 WS，会丢失 REST 天然的语义化、可缓存、可单独重试的优势。

### Agent 流式事件协议

后端发送给前端的 Agent 事件必须使用 Pydantic Model 定义，并由 Pydantic 的 alias 转换为 camelCase。当前事件及职责如下：

- `message_start`：标识一整轮 Agent 回复开始，只提供本轮 `messageId` 和创建时间；前端不能因此提前创建空的 Agent 节点
- `content_delta`：传输可见回答文本增量；前端收到本段首个增量时才创建 Agent 节点
- `tool_call_start`：提供 `messageId`、`toolCallId`、工具名称及完整参数；它同时是前一段 Agent 文本的结束边界
- `tool_call_result`：通过 `toolCallId` 更新对应工具节点，提供完整执行结果及 `isError` 状态；读取内容和错误信息都必须保留展示
- `message_end`：标识整轮 Agent 回复结束，并结束最后一段仍处于流式状态的 Agent 节点
- `error`：传输本轮处理错误；如果本轮尚未创建节点，前端应创建错误 Agent 节点，不能静默丢弃

一次 Agent 回复允许形成多个按实际发生顺序排列的节点，例如“Agent 文本 → 工具调用 → Agent 文本”。`messageId` 标识整轮回复，`toolCallId` 唯一标识单次工具调用；不要混用两者更新节点。

思考模型的 thinking 内容当前默认忽略，不进入项目 WebSocket 协议，也不创建前端节点。

---

## 后端转发原则：不要透传上游原始事件

后端与上游模型 API 交互后，**必须先转换成本项目自定义的事件协议，再推给前端**，不要把上游 SSE/流式事件原样转发。原因：

1. 解耦：以后换模型 / 换供应商，前端不用跟着改
2. 收敛复杂度：上游事件结构对前端没有意义的细节（如 content_block 索引、上游内部 id）不应该暴露给前端
3. 业务逻辑集中：落库、计费、多个 delta 聚合成完整消息，这些都在后端的 adapter 层统一处理

即使现在只对接一个上游 API，也要写这层 adapter，方便未来扩展。

---

## 类型同步

- 前端 `@/types.ts` 里与后端 Pydantic model 对应的类型，字段命名与后端保持一致（后端 Pydantic 使用 alias 转 camelCase 对应前端的类型）

---

## 前端流式输出时候的渲染

使用streamdown搭配katex实现。

聊天内容统一通过 MessageNode 节点包裹，而不是直接裸露地排列用户消息和 AI 回答：

- MessageArea 从上到下按时间顺序排列 MessageNode，形成“用户节点 → 回答节点 → 用户节点 → 回答节点”的结构
- 用户消息和 AI 回答各自占用一个独立的 MessageNode
- 所有 MessageNode 创建后都默认折叠，包括正在流式回应的新节点；只有用户点击后才展开
- AI 正在流式回应时，如果节点已由用户展开，则在节点内部实时渲染增量内容，但不能自动改变节点的展开状态
- 流式回应开始或结束都不能自动展开或折叠节点
- 流式增量更新不能触发 MessageArea 自动滚动，避免页面持续被拉向底部；滚动位置由用户控制
- 流式状态、完整内容和展开交互都应由 MessageNode 封装，MessageArea 只负责节点的顺序排列
- 工具调用必须使用独立的 MessageNode，展示工具名称、完整参数、执行结果和失败信息
- 工具节点通过 `toolCallId` 与开始/结果事件对应；一轮回复可以包含多个工具节点
- 不要在 `message_start` 时创建空 Agent 节点；应在收到首个 `content_delta` 时按需创建
- `tool_call_start` 到达时，工具之前仍处于流式状态的 Agent 节点应立即标记完成，而不是等待整轮 `message_end`
- 工具之后再次产生文本时，应创建新的 Agent 节点，从而保持“Agent → Tool → Agent”的真实顺序

---
