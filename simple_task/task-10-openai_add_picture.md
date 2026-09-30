---
created_at: 2026-09-30T19:30:40+08:00
status: done # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

现在anthropic类别的agent可以发送图片，图片使用base64编码存储于历史记录当中，然后我希望openai的也加入图片，同样base64编码存储于通用的历史记录当中，确保没有语法错误，然后我会自己测试

- 思考一下现有结构，那个历史记录是anthropic和openai通用的，你可以参考一下anthropic agent相关的实现

# 执行过程

1. 阅读项目约定、Anthropic Agent 和会话适配器，以及通用的消息模型与会话存储；确认用户图片已作为 `TextChatMessage.attachments` 中的 base64 数据保存，缺口是 OpenAI 构造请求及从历史记录恢复请求消息。
2. 在 `backend/app/ai/openai_session_adaptor.py` 增加统一的用户消息构造方法：无附件时保持原有文本格式；有附件时构造 OpenAI 消息内容列表，图片使用 `data:<media_type>;base64,<data>` 形式的 `image_url`。`to_openai` 恢复历史用户消息时复用此方法。
3. 在 `backend/app/ai/openai_agent.py` 移除不支持图片的拒绝逻辑，并用同一方法构造当前用户消息；附件参数改为 `list[Attachment]`。
4. 使用 `uv run --no-sync python` 对上述两个文件执行 AST 语法解析，结果通过；未执行上游接口测试。

# 验收反馈

测试成功！
