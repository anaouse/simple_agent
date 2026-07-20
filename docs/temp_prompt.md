1. 先不考虑模型上下文窗口配置，然后也不要加入turns字段，就加入一个简单的totalToken即可（每轮更新一次），然后现有列表包裹到messages字段当中。
2. 记得把恢复对话历史数据的代码也改一下，因为现有的对话数据就只是一个json当中存储列表，如果没有messages字段或者totalToken字段就是历史格式的数据。保持现有加载方式然后加入totalToken和messages字段，更新的时候自然而然更新。
3. 两个agent都加入get_total_token方法方便在@D:/projects/agent/backend/app/main.py 当中每轮对话获取
4. 先不考虑前端