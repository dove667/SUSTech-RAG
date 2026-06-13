"""Worker WebSocket 客户端 — 连接 Relay，接收任务并执行 RAG 推理。"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import signal
import sys
import time
import traceback
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed

from sustech_rag.relay.models import (
    build_event_msg,
    build_pong_msg,
    build_register_msg,
    build_task_done_msg,
)
from sustech_rag.worker.handler import TaskHandler


class WorkerClient:
    """Worker WebSocket 客户端。

    连接 Relay，发送注册消息，接收任务并调用 TaskHandler 执行。
    支持自动重连（固定 30s）和信号处理。
    按生成速度自动排序优先级（快的优先分配任务）。
    """

    RECONNECT_DELAY = 30.0  # 断线后固定 30s 重连

    def __init__(
        self,
        relay_url: str,
        config_path: str | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.relay_url = relay_url
        self.config_path = config_path
        self.worker_id = worker_id or f"{platform.node()}-{os.getpid()}"
        self._handler: TaskHandler | None = None
        self._running = True
        self._ws: ClientConnection | None = None
        self._capabilities: dict[str, Any] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}

        # 生成速度跟踪（用于 relay 优先级排序）
        self._total_tokens: int = 0
        self._total_gen_time: float = 0.0

        # 收集 Worker 能力信息
        self._collect_capabilities()

    def _collect_capabilities(self) -> None:
        """收集当前机器的能力信息。"""
        caps: dict[str, Any] = {
            "platform": platform.system().lower(),
            "hostname": platform.node(),
            "python": platform.python_version(),
        }

        # GPU 信息
        try:
            import torch

            if torch.cuda.is_available():
                caps["gpu"] = torch.cuda.get_device_name(0) or "CUDA GPU"
                caps["cuda_version"] = torch.version.cuda
                caps["vram_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3), 1
                )
            else:
                caps["gpu"] = "none"
                caps["vram_gb"] = 0
        except Exception:
            caps["gpu"] = "unknown"

        # LLM 后端信息 — 如果配置文件可用
        if self.config_path:
            try:
                from sustech_rag.config.loader import load_config

                app_config = load_config(self.config_path)
                caps["llm_backend"] = app_config.llm.backend
                caps["max_concurrent_requests"] = max(1, app_config.llm.max_concurrent_requests)
                if hasattr(app_config.llm, "model_path"):
                    caps["model"] = os.path.basename(app_config.llm.model_path) or "unknown"
                elif hasattr(app_config.llm, "served_model_name"):
                    caps["model"] = app_config.llm.served_model_name
            except Exception:
                pass

        self._capabilities = caps
        self._capabilities.setdefault("tokens_per_second", 0.0)
        print(f"[worker] capabilities: {caps}", flush=True)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """建立 WebSocket 连接并发送注册消息（含当前生成速度）。"""
        try:
            print(f"[worker] connecting to {self.relay_url}...", flush=True)
            self._ws = await websockets.connect(
                self.relay_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            print("[worker] connected", flush=True)

            # 更新生成速度到 capabilities
            self._capabilities["tokens_per_second"] = round(self._avg_tokens_per_sec(), 1)

            # 发送注册消息
            register_msg = build_register_msg(self.worker_id, self._capabilities)
            await self._ws.send(json.dumps(register_msg, ensure_ascii=False))

            return True
        except Exception:
            traceback.print_exc()
            return False

    def _avg_tokens_per_sec(self) -> float:
        """平均生成速度（tokens/秒）。"""
        if self._total_gen_time > 0:
            return self._total_tokens / self._total_gen_time
        return 0.0

    async def run(self) -> None:
        """主循环：连接 → 处理消息 → 断线 30s 后重连。"""
        # 初始化 TaskHandler（只初始化一次）
        print("[worker] initializing TaskHandler...", flush=True)
        self._handler = TaskHandler(self.config_path)
        print("[worker] TaskHandler ready", flush=True)

        while self._running:
            connected = await self.connect()
            if not connected:
                print(
                    f"[worker] connection failed, retrying in {self.RECONNECT_DELAY:.0f}s...",
                    flush=True,
                )
                await self._sleep_with_cancel(self.RECONNECT_DELAY)
                continue

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            try:
                await self._message_loop()
            except ConnectionClosed as e:
                print(f"[worker] connection closed: {e}", flush=True)
            except Exception:
                traceback.print_exc()
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            if self._running:
                print(
                    f"[worker] reconnecting in {self.RECONNECT_DELAY:.0f}s...",
                    flush=True,
                )
                await self._sleep_with_cancel(self.RECONNECT_DELAY)

        print("[worker] shutting down", flush=True)

    # ------------------------------------------------------------------
    # 消息处理
    # ------------------------------------------------------------------

    async def _message_loop(self) -> None:
        """持续接收 Relay 消息并分发处理。"""
        assert self._ws is not None
        async for raw in self._ws:
            try:
                msg: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                print(f"[worker] invalid json from relay: {raw[:200]}", flush=True)
                continue

            msg_type = msg.get("type", "")

            if msg_type == "registered":
                print(
                    f"[worker] registered as {msg.get('worker_id', self.worker_id)}",
                    flush=True,
                )

            elif msg_type == "task":
                task_id = msg.get("task_id", "")
                request = msg.get("request", {})
                # 创建异步任务处理（不 await，避免阻塞消息循环）
                if task_id:
                    task = asyncio.create_task(self._handle_task(task_id, request))
                    self._active_tasks[task_id] = task

            elif msg_type == "cancel":
                task_id = msg.get("task_id", "")
                if task_id:
                    assert self._handler is not None
                    if self._handler.cancel_task(task_id):
                        print(f"[worker] task cancelled: {task_id}", flush=True)
                    else:
                        print(
                            f"[worker] cancel ignored (not found): {task_id}",
                            flush=True,
                        )

            elif msg_type == "ping":
                assert self._ws is not None
                await self._ws.send(json.dumps(build_pong_msg(), ensure_ascii=False))

    async def _handle_task(self, task_id: str, request: dict[str, Any]) -> None:
        """执行单个 RAG 任务并发送事件回 Relay，同时跟踪生成速度。"""
        assert self._handler is not None
        print(f"[worker] handling task: {task_id}", flush=True)

        task_tokens = 0
        task_start = time.time()

        async def send_event(event_type: str, data: dict[str, Any] | None = None) -> None:
            """将事件通过 WebSocket 发送回 Relay。"""
            nonlocal task_tokens
            # 统计生成的 token 数
            if event_type == "content.delta" and isinstance(data, dict):
                text = data.get("text", "")
                # 粗略估算 token 数（中英文混合约 2 字符/token）
                task_tokens += max(1, len(text) // 2)
            elif event_type == "done" and isinstance(data, dict):
                usage = data.get("usage", {})
                if usage.get("completion_tokens", 0) > 0:
                    task_tokens = usage["completion_tokens"]

            msg = build_event_msg(task_id, event_type, data)
            if self._ws is not None:
                try:
                    await self._ws.send(json.dumps(msg, ensure_ascii=False))
                except Exception:
                    traceback.print_exc()

        try:
            await self._handler.handle_task(task_id, request, send_event)
        except Exception:
            traceback.print_exc()
            await send_event(
                "error",
                {"code": "server_error", "message": traceback.format_exc()},
            )
            await send_event(
                "done",
                {"finish_reason": "error", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
            )
        finally:
            # 更新生成速度统计
            elapsed = time.time() - task_start
            if task_tokens > 0 and elapsed > 0:
                self._total_tokens += task_tokens
                self._total_gen_time += elapsed
                tps = task_tokens / elapsed
                new_avg = self._avg_tokens_per_sec()
                print(
                    f"[worker] task {task_id}: {task_tokens} tokens in {elapsed:.1f}s "
                    f"({tps:.1f} t/s, avg {new_avg:.1f} t/s)",
                    flush=True,
                )

            # 发送任务完成确认
            done_msg = build_task_done_msg(task_id)
            if self._ws is not None:
                try:
                    await self._ws.send(json.dumps(done_msg, ensure_ascii=False))
                except Exception:
                    pass
            self._active_tasks.pop(task_id, None)
            print(f"[worker] task done: {task_id}", flush=True)

    # ------------------------------------------------------------------
    # 心跳
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """定期回复 Relay 的 ping 消息（通过消息循环自动处理）。"""
        # 心跳由 websockets 库的 ping_interval 和消息循环中的手动 ping/pong 共同维护。
        # 这里不需要额外逻辑，仅占位以确保心跳任务持续运行。
        while self._running and self._ws is not None:
            await asyncio.sleep(15)
            # 主动发送 pong 确保连接活跃
            if self._ws is not None:
                try:
                    await self._ws.send(json.dumps(build_pong_msg(), ensure_ascii=False))
                except Exception:
                    break

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    async def _sleep_with_cancel(self, delay: float) -> None:
        """可被取消的 sleep。"""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass

    def shutdown(self) -> None:
        """优雅关闭。"""
        self._running = False
        print("[worker] shutdown requested", flush=True)


# ---------------------------------------------------------------------------
# 同步入口
# ---------------------------------------------------------------------------

def run_worker(
    relay_url: str,
    config_path: str | None = None,
    worker_id: str | None = None,
) -> None:
    """同步入口：创建 WorkerClient 并启动事件循环。"""
    client = WorkerClient(
        relay_url=relay_url,
        config_path=config_path,
        worker_id=worker_id,
    )

    async def _main() -> None:
        # 注册信号处理
        loop = asyncio.get_running_loop()

        def _signal_handler() -> None:
            print("[worker] received interrupt, shutting down...", flush=True)
            client.shutdown()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                # Windows 不支持 add_signal_handler
                signal.signal(sig, lambda _s, _f: _signal_handler())

        await client.run()

    asyncio.run(_main())
