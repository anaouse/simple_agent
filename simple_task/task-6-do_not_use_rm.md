---
created_at: 2026-08-16T10:21:13+08:00
status: todo # done | todo
---

> 你负责记录实现过程，人负责验收，记录最新状况与后续计划、修改status

# 目的

提醒agent不要使用 `rm` 命令，就算是没用的文件也保持着

在bash命令检查下和 .git 一起检查，如果用来提醒说不能用，以及 ai/ 当中两个agent的自带系统提示词也插入一下说明不要用 rm 命令

---

## 操作记录

2026-08-16 完成以下修改：

1. `backend/app/tools/bash.py`
   - `_validate_command` 在 `.git` 检查之后新增 rm 检查：用 `shlex.split` 解析命令 token，命中独立的 `rm` token 时返回 `Error: 不要使用 rm 命令，即使看起来没用的文件也保留着`（避免误伤 `transform`、`platform` 等含 "rm" 子串的单词）
   - `bash` 的 docstring 同步更新：rejected 条件由 "operate on .git folders" 扩展为 "operate on .git folders or use rm"

2. `backend/app/ai/openai_agent.py` / `backend/app/ai/anthropic_agent.py`
   - `_build_system_prompt` 的 project_section 中新增 `## 文件操作` 小节：`不要使用 rm 命令删除文件，即使看起来没用的文件也保留着`

# 待人工验收

- bash 工具执行含 `rm` 的命令应被拦截并提示
- 不含 `rm` 的普通命令（如 `ls`、`git status`、含 "rm" 子串的单词）不受影响
- agent 的系统提示词已包含不要用 rm 的说明

# 验收

验收成功！