"""中继 FastAPI 服务 — WebSocket Worker 端点 + HTTP SSE 转发 + 管理接口。

本服务**不加载任何模型**，仅做请求路由。
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.websockets import WebSocketState

from sustech_rag.relay.models import (
    build_cancel_msg,
    build_event_msg,
    build_ping_msg,
    build_pong_msg,
    build_task_msg,
)
from sustech_rag.relay.worker_pool import WorkerPool


def _cors_origins() -> list[str]:
    """返回允许的 CORS 来源。"""
    defaults = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    extra = os.environ.get("RELAY_CORS_ORIGINS", "").strip()
    if extra:
        defaults.extend(origin.strip() for origin in extra.split(",") if origin.strip())
    return defaults


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_relay_app() -> FastAPI:
    """创建完整的中继 FastAPI 应用。"""

    pool = WorkerPool()

    # 启动心跳检查
    pool.start_heartbeat_checker(interval=30, timeout=90)

    app = FastAPI(
        title="SUSTech RAG Relay",
        summary="RAG 中继服务 — 将请求从公有云转发到本地 GPU Worker",
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # WebSocket 端点 — Worker 连接
    # ------------------------------------------------------------------

    @app.websocket("/ws/worker")
    async def ws_worker(websocket: WebSocket) -> None:
        """Worker 通过此端点与 Relay 建立 WebSocket 连接。"""
        await websocket.accept()
        print("[relay] new WebSocket connection accepted", flush=True)

        worker_id: str | None = None
        task_events: dict[str, asyncio.Queue] = app.state.task_events

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg: dict[str, Any] = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"[relay] invalid json from ws: {raw[:200]}", flush=True)
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "register":
                    worker_id = msg.get("worker_id", "")
                    capabilities = msg.get("capabilities", {})
                    pool.register(worker_id, capabilities, websocket)
                    # 发送注册确认
                    reply = {
                        "type": "registered",
                        "worker_id": worker_id,
                    }
                    await _safe_send_json(websocket, reply)

                elif msg_type == "pong":
                    if worker_id:
                        pool.update_heartbeat(worker_id)

                elif msg_type == "task_done":
                    tid = msg.get("task_id", "")
                    # 只发送 sentinel，不在此处标记空闲
                    # （空闲标记统一由 done/error 事件处理，避免竞态）
                    if tid in task_events:
                        await task_events[tid].put(None)  # Sentinel

                elif msg_type == "event":
                    tid = msg.get("task_id", "")
                    event_name = msg.get("event", "")
                    event_data = msg.get("data", {})
                    if tid in task_events:
                        await task_events[tid].put((event_name, event_data))

                    # done / error 事件时标记 worker 空闲
                    if event_name in ("done", "error") and worker_id:
                        pool.mark_idle(worker_id, task_id=tid)

                else:
                    print(
                        f"[relay] unknown message type from worker {worker_id}: {msg_type}",
                        flush=True,
                    )

        except WebSocketDisconnect:
            print(f"[relay] WebSocket disconnected: {worker_id}", flush=True)
        except Exception:
            import traceback

            traceback.print_exc()
        finally:
            if worker_id:
                pool.unregister(worker_id)

    # ------------------------------------------------------------------
    # HTTP API — 健康检查
    # ------------------------------------------------------------------

    @app.get("/api/health")
    async def api_health(response: Response) -> dict[str, Any]:
        """返回中继服务及已连接 Worker 的健康状态。"""
        workers = pool.get_all_workers()
        idle = sum(1 for w in workers if w.active_tasks < w.max_concurrent)
        busy = len(workers) - idle
        return {
            "status": "ok" if workers else "degraded",
            "relay": "running",
            "workers": len(workers),
            "workers_idle": idle,
            "workers_busy": busy,
        }

    # ------------------------------------------------------------------
    # HTTP API — 身份分配
    # ------------------------------------------------------------------

    @app.post("/api/identity")
    async def api_identity() -> dict[str, str]:
        """分配一个新的身份 ID。"""
        return {"identity_id": uuid.uuid4().hex}

    # ------------------------------------------------------------------
    # HTTP API — 知识库列表（中继不管理知识库）
    # ------------------------------------------------------------------

    @app.get("/api/knowledge-bases")
    async def api_knowledge_bases() -> list:
        """返回空列表 — 中继不管理知识库。"""
        return []

    # ------------------------------------------------------------------
    # HTTP API — Worker 列表（调试）
    # ------------------------------------------------------------------

    @app.get("/api/workers")
    async def api_workers() -> list[dict[str, Any]]:
        """调试端点：返回所有 Worker 的详细信息。"""
        return [
            {
                "worker_id": w.worker_id,
                "capabilities": w.capabilities,
                "active_tasks": w.active_tasks,
                "max_concurrent": w.max_concurrent,
                "connected_at": w.connected_at,
                "last_heartbeat": w.last_heartbeat,
            }
            for w in pool.get_all_workers()
        ]

    # ------------------------------------------------------------------
    # HTTP API — 流式问答（SSE）
    # ------------------------------------------------------------------

    @app.post("/api/chat/completions")
    async def api_chat_completions(
        body: dict[str, Any],
        request: Request,
        response: Response,
    ) -> Response:
        """基于对话消息生成 SSE 流式回答。

        1. 从 WorkerPool 获取空闲 Worker
        2. 若无可用 Worker 返回 503
        3. 通过 WebSocket 向 Worker 发送任务
        4. 将 Worker 事件转为 SSE 帧流式返回
        """
        # 检查 stream 参数
        stream = body.get("stream", False)
        if not stream:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return Response(
                content=json.dumps({"code": "bad_request", "message": "stream must be true"}),
                media_type="application/json",
            )

        # 获取空闲 Worker
        worker = pool.get_available_worker()
        if worker is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(
                content=json.dumps(
                    {"code": "no_worker", "message": "no available workers"}
                ),
                media_type="application/json",
            )

        # 生成任务 ID
        task_id = f"t_{uuid.uuid4().hex[:16]}"
        conversation_id = body.get("conversation_id") or f"c_{uuid.uuid4().hex[:16]}"
        message_id = f"m_{uuid.uuid4().hex[:16]}"
        identity_id = request.headers.get("X-Identity-ID", "")

        # 标记 Worker 忙碌
        worker_id = worker.worker_id
        if not pool.mark_busy(worker_id, task_id):
            # 竞争失败
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(
                content=json.dumps(
                    {"code": "no_worker", "message": "worker became busy"}
                ),
                media_type="application/json",
            )

        # 创建事件队列
        queue: asyncio.Queue = asyncio.Queue()
        app.state.task_events[task_id] = queue

        # 通过 WebSocket 发送任务
        task_msg = build_task_msg(
            task_id,
            {
                "messages": body.get("messages", []),
                "conversation_id": conversation_id,
                "identity_id": identity_id,
            },
        )
        send_ok = await _safe_send_json(worker.websocket, task_msg)
        if not send_ok:
            pool.mark_idle(worker_id, task_id=task_id)
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(
                content=json.dumps(
                    {"code": "worker_disconnected", "message": "worker connection lost"}
                ),
                media_type="application/json",
            )

        async def sse_event_stream():
            """异步生成器：从队列读取事件并转为 SSE 帧。"""
            try:
                # 发送 start 事件
                start_frame = _sse_frame(
                    "start",
                    {"conversation_id": conversation_id, "message_id": message_id},
                )
                yield start_frame

                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=10)
                    except asyncio.TimeoutError:
                        # 发送心跳注释保持连接
                        yield ": heartbeat\n\n"
                        continue

                    if item is None:
                        # 任务完成哨兵
                        break

                    event_name, event_data = item

                    # 将 Worker 事件映射为 SSE 事件
                    sse_event = event_name
                    sse_data = event_data

                    if event_name == "reference":
                        sse_data = {"items": event_data.get("items", event_data)}
                    elif event_name in ("think.delta", "content.delta"):
                        # 确保 data 中包含 text 字段
                        if isinstance(event_data, str):
                            sse_data = {"text": event_data}

                    yield _sse_frame(sse_event, sse_data)

                    if event_name in ("done", "error"):
                        break

            except asyncio.CancelledError:
                # 客户端断开 — 发送取消消息给 Worker
                cancel_msg = build_cancel_msg(task_id)
                await _safe_send_json(worker.websocket, cancel_msg)
                yield _sse_frame(
                    "error",
                    {"code": "cancelled", "message": "client disconnected"},
                )
                yield _sse_frame(
                    "done",
                    {
                        "finish_reason": "cancelled",
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    },
                )
            except Exception:
                import traceback

                traceback.print_exc()
                yield _sse_frame(
                    "error",
                    {"code": "server_error", "message": "internal relay error"},
                )
            finally:
                # 清理
                app.state.task_events.pop(task_id, None)
                pool.mark_idle(worker_id, task_id=task_id)

        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ------------------------------------------------------------------
    # HTTP API — 取消生成
    # ------------------------------------------------------------------

    @app.post("/api/chat/cancel")
    async def api_chat_cancel(
        body: dict[str, Any],
        response: Response,
    ) -> dict[str, Any]:
        """取消指定任务。"""
        task_id = body.get("task_id", "")
        if not task_id:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"code": "bad_request", "message": "task_id is required"}

        target_worker = pool.get_worker_for_task(task_id)

        if target_worker is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"code": "not_found", "message": "no active task to cancel"}

        cancel_msg = build_cancel_msg(task_id)
        await _safe_send_json(target_worker.websocket, cancel_msg)

        return {"code": "cancelled", "message": "ok"}

    # ------------------------------------------------------------------
    # 应用状态初始化
    # ------------------------------------------------------------------
    app.state.task_events = {}
    app.state.pool = pool

    return app


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _sse_frame(event: str, data: dict[str, Any]) -> str:
    """构造一条 SSE 消息帧。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def _safe_send_json(websocket: Any, msg: dict[str, Any]) -> bool:
    """安全地向 WebSocket 发送 JSON 消息。返回 True 表示成功。"""
    try:
        if getattr(websocket, "client_state", None) == WebSocketState.DISCONNECTED:
            return False
        await websocket.send_text(json.dumps(msg, ensure_ascii=False))
        return True
    except Exception:
        return False
