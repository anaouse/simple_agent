---
created_at: 2026-08-14T11:31:38+08:00
status: done # done | todo
---

# 目的

目前前端鼠标只有在 MessageArea上下滑动才生效，但是我希望在外部（非sidebar区域）的时候鼠标上下滑动MessagesArea也可以上下滑动，更方便用户使用

---

## 操作记录

2026-08-14 完成，仅改动 `src/components/MessageArea.tsx`：

- 给 `.message-area` 根元素挂上 `ref`
- 新增 `useEffect`，在 `window` 上以捕获阶段监听 `wheel`（`passive: false`）：
  - 鼠标位于 `.message-area` 内部或 `.project-sidebar` 内部时不做处理，保持原生滚动（避免破坏工具结果 `pre`、sidebar 列表等嵌套滚动）
  - 其余非 sidebar 区域（header、SessionInfo、InputBox、空白处）滚动时 `preventDefault` 并将 `deltaY` 累加到 MessageArea 的 `scrollTop`

- 未改动后端，未改动 CSS