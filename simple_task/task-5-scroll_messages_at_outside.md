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

# 验收

人工测试了一下，效果有点问题，在MessagesArea区域外的滚动滚动条是直接跳跃，而在区域内则是很丝滑上下滑动效果

## 返工记录

2026-08-14 第一版问题原因与修复：

- 原因：外部滚动时直接 `scrollTop += event.deltaY`，每来一个 wheel 事件就硬跳一段，没有平滑插值；区域内是浏览器原生滚动自带平滑，所以体验不一致

### 第一次返工（lerp 方案，已弃用）

用 rAF + 目标值 lerp 每帧向目标靠近 25%，虽然能平滑，但实现偏重，被驳回。

### 第二次返工（scrollBy smooth 方案，已弃用）

外部滚动时把 `scrollTop += deltaY` 换成 `scrollBy({ top: deltaY, behavior: 'smooth' })`。发现 smooth 动画和滚轮输入脱钩，连滚时互相追赶，滑动很慢，不如原生跟手，被驳回。

### 第三次返工（当前方案，恢复 lerp）

确认 MessageArea 内部没有自定义滑动逻辑，就是 `.message-area { overflow-y: auto }` 的浏览器原生滚动（合成器线程处理，跟手）；JS 手动滚动走主线程，无法 100% 复刻原生。在"即时滚动（跳跃）"和"平滑动画（慢）"之间，最终选择 lerp 方案：

- 外部滚动把 `deltaY` 累加进 `scrollTargetRef`（clamp 到可滚动范围），用 rAF 每帧向目标靠近 25%，实现平滑缓动
- 鼠标回到消息区/sidebar 内部做原生滚动时，同步目标值并取消进行中的动画，避免两套滚动互相拉扯
- 卸载时清理 rAF

等待人工复测。

# 人工测试

完美、非常丝滑