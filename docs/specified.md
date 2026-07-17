# 项目约定文档

这是一个本地极简ai agent的前后端项目，本文档为项目统一约定，会随着项目的发展加入更多约定，没有特殊理由请严格遵守，如需打破约定请先在此文档中更新说明。

开发的时候我使用热重载开发，所以不用编译验证，有错误的话我会告诉你的

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
- 与上游模型 API（Anthropic/OpenAI 等）的交互全部封装在 `services/` 层，路由函数和 WebSocket handler 里不允许直接出现上游 SDK 调用

---

## 前端

- 使用 `@` 作为 `src/` 文件引用路径
- 不写 `useCallback` 和 `useMemo`，已启用 React Compiler 自动优化
- 跨文件引用的数据类型统一写到 `@/types.ts`
- 常规非流式请求（增删改查）用 axios，不要为了"统一"塞进 WebSocket 里
- 开发端口为 vite 默认的 `5173`
- 组件化开发，尽可能写组件，然后在page文件当中进行组装，命名例子：InputBox.tsx
- 所有组件和page的css放到css文件夹下，命名和组件名称一样，但是形态变化，例子为：input-box.css， home-page.css
- @/root.css 放置本项目的颜色变量，所有css都需要使用root.css当中的颜色变量作为颜色，如果真的需要添加颜色也请加入到 root.css当中再调用
- 所有css都在 `main.tsx` 当中引入，不要在组件内部或者page当中引入
 
---

## 实时通信设计（WebSocket）

### 什么时候用 WS，什么时候用 REST

- **WS**：agent 回复的流式输出、工具调用过程状态、需要服务端主动推送的场景
- **REST**：创建会话、获取历史消息列表等语义明确、需要幂等重试的操作

不要把所有请求都塞进 WS，会丢失 REST 天然的语义化、可缓存、可单独重试的优势。

---

## 后端转发原则：不要透传上游原始事件

后端与上游模型 API 交互后，**必须先转换成本项目自定义的事件协议，再推给前端**，不要把上游 SSE/流式事件原样转发。原因：

1. 解耦：以后换模型 / 换供应商，前端不用跟着改
2. 收敛复杂度：上游事件结构对前端没有意义的细节（如 content_block 索引、上游内部 id）不应该暴露给前端
3. 业务逻辑集中：落库、计费、多个 delta 聚合成完整消息，这些都在后端的 adapter 层统一处理

即使现在只对接一个上游 API，也要写这层 adapter（`services/stream_adapter.py`），方便未来扩展。

---

## 类型同步

- 前端 `@/types.ts` 里与后端 Pydantic model 对应的类型，字段命名与后端保持一致（后端 Pydantic 使用 alias 转 camelCase 对应前端的类型）

---

## 前端流式输出时候的渲染

使用才发现streamdown搭配katex实现

---

## 其他

- 涉及到时间的统一用 ISO 8601 UTC（比如 2026-07-18T08:30:45Z） 字符串保存或传输，前端本地转时区展示
