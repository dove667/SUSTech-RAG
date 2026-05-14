# SUSTech Campus RAG API

Base URL 由前端设置页的 `apiBaseUrl` 决定，默认是 `/api`。当前后端路由统一挂在 `/api` 前缀下。

当前实现没有内建 Authorization 鉴权；生产部署请在反向代理或后端中间件中补齐。

## POST /identity

创建一个浏览器身份 ID。前端首次加载且本地没有 `identityId` 时调用。

响应：

```json
{ "identity_id": "..." }
```

后续请求会通过请求头发送：

```text
X-Identity-ID: <identity_id>
```

## POST /chat/completions

流式问答接口。当前后端要求 `stream: true`，响应类型为 `text/event-stream`。

请求头：

```text
Content-Type: application/json
Accept: text/event-stream
X-Identity-ID: <identity_id>
```

请求体：

```json
{
  "conversation_id": "c_xxx",
  "messages": [
    { "role": "user", "content": "南科大有哪些学院？" }
  ],
  "model": "default",
  "stream": true,
  "options": {
    "temperature": 0.3,
    "top_k": 5,
    "enable_think": true,
    "enable_tools": true
  }
}
```

说明：

- `messages` 必填，后端会使用最后一条非空 `user` 消息作为检索 query。
- `conversation_id` 可选；为空时由服务端自动分配，并在 `start` 事件中返回。
- `model` 和 `options` 当前主要为前端设置和未来扩展保留；后端实际检索/生成参数主要来自 YAML 配置。
- `stream: false` 会返回 `400 bad_request`。

SSE 帧格式：

```text
event: content.delta
data: {"text":"..."}

```

当前后端实际返回的事件：

| event | data | 说明 |
|---|---|---|
| `start` | `{ "conversation_id": "...", "message_id": "..." }` | 服务端生成的会话和消息 ID |
| `reference` | `{ "items": [{ "title": "...", "url": "...", "snippet": "...", "score": 0.1 }] }` | 检索引用 |
| `think.delta` | `{ "text": "..." }` | 模型 reasoning 增量 |
| `think.end` | `{}` | reasoning 结束 |
| `content.delta` | `{ "text": "..." }` | 回答正文增量 |
| `error` | `{ "code": "...", "message": "..." }` | 流内错误 |
| `done` | `{ "finish_reason": "stop", "usage": { "prompt_tokens": 0, "completion_tokens": 0 } }` | 流结束 |

前端也保留了 `tool.call`、`tool.result` 和 `image` 事件渲染能力，但当前后端不会主动产生这些事件。

## POST /chat/cancel

请求取消正在生成的服务端消息。

```json
{
  "message_id": "m_xxx"
}
```

成功：

```json
{ "code": "cancelled", "message": "ok" }
```

没有找到活跃生成：

```json
{ "code": "not_found", "message": "no active generation to cancel" }
```

注意：`message_id` 应使用 `start` 事件里后端返回的 ID。

## GET /health

返回后端组件状态。

成功：

```json
{
  "status": "ready",
  "components": {
    "retrieval": "ok",
    "llm": "ok"
  }
}
```

未就绪或启动失败会返回 503，例如：

```json
{
  "status": "error",
  "message": "components not ready",
  "components": {}
}
```

## 错误格式

当前后端显式返回的普通 HTTP 错误通常为：

```json
{ "code": "bad_request", "message": "..." }
```

也可能返回：

```json
{ "code": "service_unavailable", "message": "..." }
```

未捕获的服务端异常会统一返回：

```json
{ "code": "internal_server_error", "message": "internal server error" }
```

请求体验证错误（例如缺少必填字段）保持 FastAPI 默认 422 格式：

```json
{
  "detail": [
    {
      "type": "...",
      "loc": ["body", "..."],
      "msg": "...",
      "input": {}
    }
  ]
}
```

流式过程中错误会通过 SSE `event: error` 返回，后续通常还会发送 `done`。
