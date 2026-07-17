uv run -m uvicorn app.main:app --reload --port 2453
只能渲染 $$ 包裹的公式

streamdown 强制依赖tailwind css，但是其他部分可以自己写css

新建一个 CSS 文件（比如 src/tailwind.css），在 main.tsx 里引入：
@import "tailwindcss";
@source "../node_modules/streamdown/dist/*.js";
@source "../node_modules/@streamdown/code/dist/*.js";
@source "../node_modules/@streamdown/math/dist/*.js";

tsx// main.tsx
import './tailwind.css'
import 'katex/dist/katex.min.css'
import 'streamdown/styles.css'
