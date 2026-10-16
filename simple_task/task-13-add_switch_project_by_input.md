---
created_at: 2026-10-16T12:05:17+08:00
status: todo # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

现在新加入项目的方法是通过把路径输入到sidebar顶部的输入栏然后确认，但其实没必要，完全可以只依靠对话的输入栏，而且我希望也可以通过对话的输入栏切换项目，而不是依靠sidebar，具体需求如下：

- 把sidebar的输入框去掉，但是项目的展示和可以点击切换，右键跳出菜单删除项目什么的都保留，ctrl+\toggle的快捷键也保留，只是去掉输入框的ui
- 一开始没有项目的时候输入栏是不能输入东西的这个改掉，可以输入东西，只不过这个时候发送消息不会进行真正的对话，只是为了方便通过输入来选择项目
- 现在对话的输入栏可以输入 `@` 来指示对应的文件，也可以通过输入 `/` 来选择切换模型或调用对应的skill，然后多加入一个 `#` 符号用来输入项目或选择已有项目进行切换（现在改动前是通过sidebar提交新的项目路径或者点击已有的项目卡片，我现在其实就是把这些逻辑放到对话输入栏来而已）
  - 具体的流程是输入 `#` 的时候类似 `@` 命令，展示已有的项目，然后我可以挑选或输入更多符号来筛选项目，最后通过tab选择已有的项目，然后发送后就进行项目切换，如果我是直接输入 `#D:/projects/new_project`在`#`后方的路径是新项目，那么就向后端发送，逻辑类似现在的sidebar输入新路径添加新项目

## 操作记录

2026-10-16 完成以下修改（前端，`npx vite build` 通过）：

1. `src/components/ProjectSidebar.tsx`：删除顶部路径输入表单、`error`/`submitting` 状态和 `axios` 依赖，删除 `onAdd` prop。保留折叠按钮（ctrl+\）、项目列表、点击切换、右键菜单删除、会话列表。
2. `src/css/project-sidebar.css`：删除 `.project-sidebar__form*` 与 `.project-sidebar__error` 规则。
3. `src/components/InputBox.tsx`：
   - props 由 `disabled` 拆成 `chatDisabled`（能否发真正的对话消息）和 `editorDisabled`（能否输入，即回答中或切换会话中）；textarea 现在只在 `editorDisabled` 时禁用，因此没有项目时也能输入。
   - 新增 `projects` 与 `onProjectOpen` 两个 prop。
   - 新增 `#` 触发器：像 `@` 一样按光标位置匹配，展示已有项目，可继续输入筛选，Tab 选中后插入 `#<项目路径> `。
   - `send()` 中：内容以 `#` 开头时解析 `#` 后面的路径并调用 `onProjectOpen(path)`，不发送对话消息，只清空输入；内容只有 `#` 时不做任何事。
   - 发送按钮在 `#` 开头且后面有路径时可点击（不受 `chatDisabled` 限制）。
   - placeholder 改为 `输入消息，使用 @ 引用文件、/ 执行命令或 # 切换项目…`。
4. `src/pages/HomePage.tsx`：
   - 新增 `openProject(path)`：路径已在项目列表中就 `selectProject`，否则 `POST /api/projects` 创建（逻辑同原 sidebar 输入新路径），成功后加入列表并切换；失败时把后端错误显示在输入栏的错误位置。
   - `InputBox` 传入 `chatDisabled={!activePath || !connected}`、`editorDisabled={responding || startingSession}`、`projects`、`onProjectOpen={openProject}`。
   - `ProjectSidebar` 去掉 `onAdd`。
   - 顶部标题在没有项目时改为 `输入 # 项目路径来添加或切换项目`。

## 待人工验收

- sidebar 只剩折叠按钮 + 项目列表（含右键菜单、会话列表），没有输入框。
- 没有项目时输入栏可以输入；此时发送普通消息不会有任何反应（内容保留），发送 `#路径` 可添加并切换项目。
- 输入 `#` 弹出已有项目列表，继续输入可筛选，Tab 选中填入 `#路径 `，回车发送后切换到该项目。
- 直接输入 `#D:/projects/new_project` 发送，会调 `POST /api/projects` 创建并切换；路径无效时输入栏显示后端错误。
- `@` 引用文件、`/model`、`/skill` 行为不变。

# 验收

成功，这个想法主要是其实只要一个输入框就可以类似命令行的感觉，所以进行这样的极简改造，舒服了。
