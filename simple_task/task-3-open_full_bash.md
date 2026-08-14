---
created_at: 2026-08-14T10:48:18+08:00
status: done # done | todo
---

# 说明

这次任务是为了完全开放bash的能力，以及修改 edit 工具

聚焦于那个 bash.py

# 我要的修改

直接不审查 agent 的 bash 命令，但是任何 bash 命令当中包含 .git 文件夹的都驳回，说不能作用于 git 文件夹

ai/ 当中的两个 agent 的系统提示词也要修改一下，不强调bash命令的限制了

然后 docs/ 当中的 system prompt 强调一下不要做过多的检查和测试，能编译成功就好，然后 python 使用 uv，而不是直接使用 python 命令

edit.py 不要多处修改了，就单个文件，单个 old_text 对一个 new_text

# 操作记录

2026-08-14 11:03 完成以下修改：

1. `backend/app/tools/bash.py`
   - 删除 `ALLOWED_COMMANDS` 白名单及命令首词校验，bash 命令不再审查
   - `_validate_command` 改为检查命令中是否包含 `.git`，命中返回 `Error: 不能作用于 git 文件夹`
   - 更新 docstring，去掉白名单相关说明

2. `backend/app/ai/anthropic_agent.py` / `backend/app/ai/openai_agent.py`
   - `_build_system_prompt` 中删除 "bash 仅允许使用工具白名单中的命令…" 一行，不再强调 bash 限制

3. `docs/system_prompt.md`
   - 工作风格新增：不要做过多的检查和测试，能编译成功就好
   - 新增 `# Python` 小节：运行 python 统一使用 `uv`，不要直接使用 `python` 命令

4. `backend/app/tools/edit.py`
   - 签名从 `edit(path, old_text: list[str], new_text: list[str])` 改为 `edit(path, old_text: str, new_text: str)`
   - 删除列表校验与顺序替换循环，只做单次 old_text → new_text 替换
   - 工具 schema 由 `tools_from_functions` 自动生成，old_text/new_text 参数类型自动变为 string，无需额外改动

# 人类测试

edit工具和bash命令没有大问题，edit工具原本的list设计显然不符合大模型本身训练数据，所以一直报错，现在只修改一块地方自然而然顺利很多