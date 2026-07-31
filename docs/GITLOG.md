# commit 2e3cf7d487285adb8acc5b7069a3df63a8804c6e Date: Wed Jul 29 12:25:07 2026 +0800

优化体验

1. 点击项目后自动创建新对话，目前逻辑是点击“新对话”按钮如果最新为空是不会重复创建的，我要的目的就是点击新项目后自动进入到空白对话，要么已存在，要么就新创建一个
2. 目前前端的InputBox“发送”按钮在模型回答的时候会变为“停止”按钮，结束后恢复“发送”按钮，你搞清楚这两个节点，现在根据这两个节点修改SessionInfo.tsx，加入一个本轮回答的时间计算单位是s，每秒更新一次，从我发送prompt，出现“停止”按钮开始到按钮恢复为“开始”。
3. 焦点在MessageArea或MessageNode的时候键盘输入 “/” 聚焦InputBox方便输入

后续调优：

commit 9d434b033d4772247096adae81665faafdb1e66a Date: Wed Jul 29 15:38:25 2026 +0800

# commit 490afc75f740f93d11ac3054817ddaec5186b1a8 Date: Fri Jul 31 11:00:07 2026 +0800

1. InputBox 的 UI “/” 修改
2. 修复 Anthropic agent 回答时候有时候工具调用错误
