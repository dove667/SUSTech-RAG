# RAG 知识问答系统 · 前端 ↔ 后端 接口规范

本文档定义了 RAG WebUI 所需的全部 HTTP / SSE 接口。前端（本仓库）严格按照本文档进行调用；后端只需按本文档实现即可无缝对接。

- Base URL：由前端"设置页"里 `apiBaseUrl` 变量决定（默认 `/api`）
- 鉴权：可选。若设置页填写了 `apiKey`，前端会在所有请求中附加 `Authorization: Bearer <apiKey>`
- 字符编码：UTF-8
- 日期格式：RFC 3339 / ISO 8601

---

## 1. 流式问答（核心接口）

> 这是整个系统最重要的接口。前端使用 `fetch` + `ReadableStream` 读取 **Server-Sent Events (SSE)**，以便在弱网、代理、无后端环境下都能工作。

### `POST /chat/completions`

#### Request Headers

| 名称 | 值 |
|---|---|
| `Content-Type` | `application/json` |
| `Accept` | `text/event-stream` |
| `Authorization` | `Bearer <apiKey>` *(可选)* |

#### Request Body

```jsonc
{
  "conversation_id": "c_2f8b1a...",   // 可选，前端会为每次新会话生成
  "messages": [
    { "role": "user",      "content": "什么是 RAG？" },
    { "role": "assistant", "content": "RAG 是..." },
    { "role": "user",      "content": "再详细解释一下" }
  ],
  "knowledge_base_ids": ["kb_default"], // 可选
  "model":  "default",                  // 可选
  "stream": true,                       // 必须为 true
  "options": {                          // 可选，透传给后端
    "temperature": 0.3,
    "top_k": 5,
    "enable_think": true,               // 是否允许返回 <think> 思考块
    "enable_tools": true                // 是否允许返回工具调用块
  }
}
```

#### Response — `text/event-stream`

服务器以 **SSE 协议** 响应，每条事件形如：

```
event: <type>
data: <json>

```

> 注意末尾有一个空行（SSE 协议要求）。

流式结束后必须发送 `event: done`。任何错误必须通过 `event: error` 通知前端，之后再结束连接。

### 事件类型一览

| event | data 结构 | 说明 |
|---|---|---|
| `start` | `{ "conversation_id": "c_...", "message_id": "m_..." }` | 流开始。前端会创建一个 assistant 消息占位 |
| `think.delta` | `{ "text": "..." }` | 思考链文本增量（会被渲染为可折叠的 think 块） |
| `think.end`   | `{}` | 思考结束 |
| `content.delta` | `{ "text": "..." }` | 正文文本增量（Markdown / LaTeX 混合文本） |
| `tool.call` | `{ "id": "t_1", "name": "search_kb", "arguments": { ... } }` | 工具调用开始 |
| `tool.result` | `{ "id": "t_1", "result": { ... } }` | 工具调用结果 |
| `image` | `{ "url": "https://...", "alt": "示意图", "caption": "..." }` | 图片块（可多次） |
| `reference` | `{ "items": [{ "title":"...", "url":"...", "snippet":"...", "score":0.82 }] }` | 检索到的知识引用 |
| `done`  | `{ "finish_reason": "stop \| length \| error", "usage": { "prompt_tokens": 128, "completion_tokens": 456 } }` | 流结束 |
| `error` | `{ "code": "rate_limited", "message": "..." }` | 错误；前端会展示为错误块 |

#### 示例流片段

```
event: start
data: {"conversation_id":"c_1","message_id":"m_9"}

event: think.delta
data: {"text":"我需要先检索相关文档..."}

event: think.end
data: {}

event: tool.call
data: {"id":"t_1","name":"search_kb","arguments":{"q":"RAG"}}

event: tool.result
data: {"id":"t_1","result":{"hits":3}}

event: content.delta
data: {"text":"**RAG**（Retrieval Augmented Generation）是一种..."}

event: content.delta
data: {"text":"其核心公式为 $P(y|x)=\\sum_z P(y|x,z)P(z|x)$。"}

event: image
data: {"url":"https://example.com/rag.png","alt":"RAG 架构图"}

event: reference
data: {"items":[{"title":"RAG 论文","url":"https://arxiv.org/abs/2005.11401","snippet":"..."}]}

event: done
data: {"finish_reason":"stop","usage":{"prompt_tokens":128,"completion_tokens":456}}
```

> **渲染规则（前端内建）**：正文文本会被合并为一整段 Markdown，再交给富文本渲染器；LaTeX 自动识别 `$...$`、`$$...$$`、`\(...\)`、`\[...\]`、以及裸露的 `\begin{equation}...\end{equation}` 等多种包裹。

---

## 2. 中止流式生成

### `POST /chat/cancel`

请求体：

```json
{ "conversation_id": "c_2f8b1a...", "message_id": "m_9" }
```

返回 `204 No Content`。

> 前端同时会直接 `AbortController.abort()` 掉 SSE 连接，此接口用于通知后端停止计算。后端若未实现，直接返回 204 即可。

---

## 3. 会话管理（可选，前端默认走本地存储）

### `GET /conversations`

返回：

```json
{
  "items": [
    { "id":"c_1", "title":"关于 RAG", "updated_at":"2026-04-20T10:00:00Z" }
  ]
}
```

### `GET /conversations/{id}`

返回单条会话的完整消息列表。

### `POST /conversations`

```json
{ "title": "新会话" }
```

返回：`{ "id": "c_..." }`。

### `DELETE /conversations/{id}`

`204`。

---

## 4. 知识库列表（可选）

### `GET /knowledge_bases`

```json
{
  "items": [
    { "id": "kb_default", "name": "默认库", "doc_count": 128 }
  ]
}
```

---

## 5. 错误响应规范

所有非 2xx 响应统一为：

```json
{ "code": "some_error_code", "message": "人类可读的错误信息" }
```

常见 code：`bad_request` / `unauthorized` / `rate_limited` / `server_error`。

---

## 6. 前端对"后端未实现"的降级行为

- 若 `fetch /chat/completions` 失败，会自动退化到**本地 Demo 模式**（随机生成包含 think / 代码 / LaTeX / 图片 / 工具块的示例流），方便在无后端时预览 UI。
- 会话接口 (`/conversations*`) 若失败，前端会使用 `localStorage` 保存历史。

---

## 7. 安全建议

- 推荐部署在 HTTPS 下；SSE 在 HTTP/2 上性能更好
- 浮动精灵球 / 嵌入模式会以 `postMessage` 与父页面通信，后端无需关心
- `apiKey` 只存在浏览器本地，请通过反向代理 + 源站白名单加固
