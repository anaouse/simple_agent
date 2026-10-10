---
created_at: 2026-10-10T11:19:20+08:00
status: done # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

- 要在 tools 文件夹下新加入一个 read_picture 工具用来读取图片文件
- 现在可以在前端使用粘贴把图片作为附件结合消息一起发送，然后使用base64编码把图片作为数据存储在历史记录当中，然后read_picture的作用也是让模型可以直接读取图片变为并且变为base64编码保存在历史数据以及走图片读取的的api
- 记得兼容 openai 和 anthropic 两类agent，但好像变为 base64 就可以了
- 参考其他 tools 看看工具说明的格式是什么

我的设计的伪代码，如果你觉得不好或者是不是加入什么说明比较好你也可以修改

```python
def read_picture(path: str):
    """
    path 就是图片文件的完整路径
    """
    try:
        image = load_picture(path)
        base64_data = encode(image)
        return base64_data
    except:        
        # 这里解析失败之后是不是就不走图片api了？总之你看着办
        return "路径不存在或路径不是图片或解析失败"
```

改好后确保没有语法错误然后我来验证

## 执行记录

### 2026-10-09

- 新增 `backend/app/tools/read_picture.py`，使用与现有工具一致的 Google-style docstring，参数为图片完整绝对路径。
- 使用 Pillow 验证图片格式并检查解码。支持 PNG、JPEG、GIF、WebP；路径不存在、不是文件、格式不支持或解码失败时返回错误文本，不发送图片内容。
- 成功结果为 JSON 字符串，包含路径、实际媒体类型及 base64 数据。复用现有工具结果事件和历史记录的 `result` 字段保存，不修改历史数据结构。
- 在 OpenAI 和 Anthropic Agent 中注册工具。
- OpenAI：工具响应保留简短说明，在全部工具响应之后添加包含 data URL 的图片消息，避免把 base64 当作普通文本传入模型。
- Anthropic：在 `tool_result` 内使用 base64 image 内容块。
- 两类 session adaptor 复用相同图片结果转换逻辑，重新打开历史记录时直接使用保存的 base64，不依赖原图片文件。
- 新增 Pillow 依赖并更新 `backend/uv.lock`。
- 已运行 `cd backend && uv run --no-sync -m compileall -q app`，通过语法检查。未调用真实模型 API，图片识别效果和历史恢复效果待人工验收。
- 保持 `status: todo`，等待人工验收后手动修改。
