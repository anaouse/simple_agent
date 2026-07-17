INFO:     127.0.0.1:58556 - "WebSocket /ws/chat?project_path=D%3A%2Fprojects%2Ftest" [accepted]
INFO:     connection open
2026-07-17 19:25:02.950 | INFO     | app.main:chat:130 - User message received
2026-07-17 19:25:02.953 | INFO     | app.ai.anthropic_agent:reply:63 - Upstream API call started
2026-07-17 19:25:05.222 | INFO     | app.ai.anthropic_agent:reply:81 - Upstream API call completed
2026-07-17 19:25:16.165 | INFO     | app.main:chat:180 - WebSocket disconnected
INFO:     127.0.0.1:48327 - "WebSocket /ws/chat?project_path=D%3A%2Fprojects%2Fdaily" [accepted]
INFO:     connection open
2026-07-17 19:25:18.750 | INFO     | app.main:chat:127 - Project switched: D:\projects\daily
2026-07-17 19:25:23.606 | INFO     | app.main:chat:130 - User message received
2026-07-17 19:25:23.608 | INFO     | app.ai.anthropic_agent:reply:63 - Upstream API call started
2026-07-17 19:25:47.606 | INFO     | app.ai.anthropic_agent:reply:81 - Upstream API call completed

切换项目的时候会出现卡住挺久的情况，感觉是初始化的问题？
