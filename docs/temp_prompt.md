端口规划
    Deploy  Dev
后端  2453（不变）    2454（新）
前端  5000（vite preview，不变）   5173（vite dev，不变）
需要修改的四个层面
1. dev.bat — 不杀部署版，后端改用 2454

    kill 端口列表：从 5000 2453 改为 5000 2454。因为不再杀 2453（那是部署版后端），改为杀 2454（防止上次 dev 没关干净）。5000 保留不动（npm run build && vite preview 可能不会占用 5000，但 kill 一下无害）。
    后端启动命令：--port 2453 改为 --port 2454。

2. deploy.vbs — 加 kill 逻辑，先杀再重启

当前 deploy.vbs 直接 Run，没有杀旧进程。如果旧部署版还在跑，新进程会端口冲突启动失败。需要在 shell.Run 之前加入类似 dev.bat 的 kill 逻辑（杀 5000 和 2453），然后才启动。VBS 里杀端口需要用 WScript.Shell.Exec 跑 netstat + taskkill，写法比 bat 啰嗦一些。
3. 前端 — 区分 dev 和 preview 的后端端口

这是最关键的一层。当前 HomePage.tsx 硬编码了 2453：
ts

const API_BASE_URL = `${location.protocol}//${location.hostname}:2453/api`
const WS_BASE_URL = `...${location.hostname}:2453/ws/chat`

推荐方案：用 Vite 环境变量文件

    新建 .env.development：VITE_BACKEND_PORT=2454（npm run dev 自动加载）
    新建 .env.production：VITE_BACKEND_PORT=2453（npm run build / vite preview 自动加载）

HomePage.tsx 改为：
ts

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '2453'
const API_BASE_URL = `${location.protocol}//${location.hostname}:${BACKEND_PORT}/api`
const WS_BASE_URL = `...${location.hostname}:${BACKEND_PORT}/ws/chat`

这样 npm run dev 时自动连 2454（dev 后端），vite preview 时自动连 2453（deploy 后端），不需要改 dev.bat 传环境变量，也不需要在 package.json 的 scripts 里加额外参数。Vite 本身就按 mode 自动加载对应的 .env.* 文件。

    注意：.env.development 和 .env.production 建议加入 .gitignore（如果还没加的话），VITE_ 前缀的变量才会暴露给前端代码，这是 Vite 的安全设计。

4. specified.md — 更新端口约定

当前文档写"服务端口固定为 2453"，现在 dev 多了个 2454，建议改成类似：

        部署环境后端端口固定为 2453，开发环境后端端口为 2454

不需要改的地方

    main.py CORS：allow_origins 已包含 localhost:5173 和 localhost:5000，dev 和 deploy 前端都已覆盖，不需改动。
    vite.config.ts：没有硬编码端口，不需改动。
    DATA_DIR：两个实例共享 data/ 目录。只要不同时对同一个 project_path 操作，不会有冲突。如果你经常用部署版 agent 开发当前 agent 项目，建议注意 session 数据可能混在一起（不过通常影响不大，因为部署版操作的是 agent 项目本身，开发版操作其他项目）。

潜在风险点

    VBS 杀进程的可靠性：netstat -ano | findstr 在 VBS 里需要用 Exec 然后读 StdOut，不像 bat 的 for /f 那么直接。可以考虑在外面写一个独立的 .bat 做 kill，deploy.vbs 调用它。
    前端还有其他地方硬编码 2453 吗：目前初步搜索只有 HomePage.tsx 的两处。改了 VITE_BACKEND_PORT 后全局统一。