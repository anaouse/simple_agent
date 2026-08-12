---
created_at: 2026-08-13T00:16:54+08:00
status: done # done | todo
---

# 目的

目前前端展示项目的sidebar位于左边，我想要放到右边去，记得那个收缩的箭头也应该要变化一下

然后加入快捷键 ctrl+\ toggle 右边sidebar

---

## 过程记录

- 2026-08-13 完成
  - `src/pages/HomePage.tsx`：
    - JSX 顺序调整，`home-page` 在前、`ProjectSidebar` 在后，sidebar 渲染到右侧
    - 全局 keydown 监听中新增 `ctrl+\` 快捷键，切换 `sidebarCollapsed`（不受输入框焦点影响，`preventDefault` 避免浏览器默认行为）
  - `src/components/ProjectSidebar.tsx`：收缩箭头左右镜像，展开显示 `›`、收起显示 `‹`
  - `src/css/project-sidebar.css`：
    - 边框 `border-right` → `border-left`
    - toggle 按钮 `right: -14px` → `left: -14px`，贴住内容侧边缘
  - 仅改动前端，后端无涉及