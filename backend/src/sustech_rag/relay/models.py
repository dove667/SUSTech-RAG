"""中继服务数据模型 — Worker 信息、任务请求与 WebSocket 消息格式。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkerInfo:
    """已连接的 Worker 状态。

    Attributes:
        worker_id: Worker 唯一标识（如 win-gpu-01-12345）。
        capabilities: Worker 能力声明（平台、GPU、模型等）。
        websocket: 与该 Worker 建立的 WebSocket 连接对象。
        connected_at: 连接建立时间戳。
        last_heartbeat: 最近一次心跳时间戳。
        active_tasks: 当前正在处理的任务数。
        max_concurrent: 该 Worker 允许的最大并发任务数。
    """

    worker_id: str
    capabilities: dict[str, Any]
    websocket: Any  # starlette / fastapi WebSocket 对象
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    active_tasks: int = 0
    max_concurrent: int = 1

    @property
    def is_busy(self) -> bool:
        """向后兼容：是否已达到并发上限。"""
        return self.active_tasks >= self.max_concurrent


@dataclass
class TaskRequest:
    """中继转发的任务请求。

    Attributes:
        task_id: 任务唯一 ID。
        messages: ChatML 格式的消息列表。
        conversation_id: 会话 ID。
        identity_id: 浏览器身份 ID。
    """

    task_id: str
    messages: list[dict[str, str]]
    conversation_id: str | None = None
    identity_id: str | None = None


# ---------------------------------------------------------------------------
# WebSocket 消息构造工具
# ---------------------------------------------------------------------------

def build_register_msg(worker_id: str, capabilities: dict[str, Any]) -> dict[str, Any]:
    """构造 Worker → Relay 的注册消息。"""
    return {"type": "register", "worker_id": worker_id, "capabilities": capabilities}


def build_registered_msg(worker_id: str) -> dict[str, Any]:
    """构造 Relay → Worker 的注册确认消息。"""
    return {"type": "registered", "worker_id": worker_id}


def build_task_msg(task_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """构造 Relay → Worker 的任务分配消息。"""
    return {"type": "task", "task_id": task_id, "request": request}


def build_event_msg(task_id: str, event: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造 Worker → Relay 的流式事件消息。"""
    msg: dict[str, Any] = {"type": "event", "task_id": task_id, "event": event}
    if data is not None:
        msg["data"] = data
    return msg


def build_cancel_msg(task_id: str) -> dict[str, Any]:
    """构造 Relay → Worker 的取消任务消息。"""
    return {"type": "cancel", "task_id": task_id}


def build_ping_msg() -> dict[str, Any]:
    """构造 Relay → Worker 的心跳 Ping 消息。"""
    return {"type": "ping"}


def build_pong_msg() -> dict[str, Any]:
    """构造 Worker → Relay 的心跳 Pong 消息。"""
    return {"type": "pong"}


def build_task_done_msg(task_id: str) -> dict[str, Any]:
    """构造 Worker → Relay 的任务完成确认消息。"""
    return {"type": "task_done", "task_id": task_id}
