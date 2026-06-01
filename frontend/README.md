# SUSTech Campus RAG Frontend

Vue 3 + Vite 前端，为 RAG 后端提供桌面、移动、嵌入和悬浮入口。前端通过 `fetch` 读取后端 SSE 流，把引用、思考块和正文增量渲染到聊天界面。

## 技术栈

- Vue 3
- Vite
- Pinia
- Vue Router
- Marked + DOMPurify
- KaTeX
- Highlight.js

## 安装与启动

```bash
cd frontend
npm install
npm run dev
```

默认端口是 `3000`。开发环境下 `/api` 会由 Vite 代理到 `http://127.0.0.1:8001`。

生产构建：

```bash
npm run build
npm run preview
```

仓库根目录的 `entrypoint.sh` 也是前端启动脚本：

```bash
bash ../entrypoint.sh
bash ../entrypoint.sh production
```

它只会进入 `frontend/` 并运行 Vite 开发服务器或生产预览，不会启动后端。

## 页面入口

- `/`：桌面版聊天界面
- `/mobile`：移动版聊天界面
- `/settings`：设置页
- `/embed`：整页嵌入版
- `/ball`：悬浮入口
- `/binarize.html`：独立静态工具页

`App.vue` 会在桌面版和移动版之间按窗口宽度自动切换，嵌入页、悬浮页和设置页不参与自动切换。

## 与后端联调

先启动后端：

```bash
cd ../backend
uv run sustech-rag serve --host 127.0.0.1 --port 8001
```

再启动前端：

```bash
cd ../frontend
npm run dev
```

设置页里的 `API Base URL` 默认是 `/api`。如果前端和后端不在同一个 origin，可以改成完整地址，例如：

```text
http://127.0.0.1:8001/api
```

后端 CORS 默认允许：

- `http://127.0.0.1:3000`
- `http://localhost:3000`

## 状态与存储

前端使用浏览器 `localStorage` 保存：

- 聊天会话：`ragwebui:chats:v1`
- 用户设置：`ragwebui:settings:v1`

首次加载时会请求 `POST /api/identity` 获取身份 ID；后端不可用时会生成本地 fallback ID。

## SSE 事件

当前前端支持这些事件：

- `start`
- `reference`
- `think.delta`
- `think.end`
- `content.delta`
- `tool.call`
- `tool.result`
- `image`
- `error`
- `done`

当前后端实际主要返回 `start`、`reference`、`think.delta`、`think.end`、`content.delta`、`error` 和 `done`。

详细协议见 [../docs/API.md](../docs/API.md)。`public/API.md` 是给浏览器直接访问的同内容副本。

## 常见问题

`vite: command not found`：说明 `node_modules` 不存在，先运行 `npm install`。

无法连接后端：确认后端服务已启动，设置页 `API Base URL` 为 `/api` 或完整的后端 `/api` 地址。

取消生成只停止了前端显示：前端会先 abort 当前 SSE 连接，再调用 `/chat/cancel` 通知后端。取消是否能真正停止计算取决于后端是否使用了同一个服务端 `message_id`。

## 代码入口

```text
src/main.js                  Vue 入口
src/App.vue                  主题、身份和路由切换初始化
src/router/index.js          路由
src/stores/chat.js           会话、发送、取消、流式消息组装
src/stores/settings.js       设置、主题、API 参数
src/utils/chatClient.js      HTTP/SSE 客户端
src/utils/sse.js             SSE parser
src/components/              聊天 UI 组件
src/views/                   页面视图
```
