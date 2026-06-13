"""Worker 任务处理器 — 封装 RagService，执行 RAG Pipeline 并支持取消。"""

from __future__ import annotations

import threading
import traceback
from typing import Any, Callable, Coroutine

from sustech_rag.config.loader import load_config
from sustech_rag.config.models import AppConfig
from sustech_rag.pipeline.rag_service import GenerationCancelledError, RagService


class TaskHandler:
    """在 Worker 进程中执行 RAG 推理任务。

    每个任务通过 `threading.Event` 实现取消，与 RagService 的 cancel_event 参数兼容。
    会启动后台 LLM 服务并保持常驻以供后续任务复用。
    """

    def __init__(self, config: AppConfig | str | None = None) -> None:
        """初始化 RAG 服务。

        Args:
            config: AppConfig 实例或 YAML 配置文件路径。为 None 时加载默认配置。
        """
        if isinstance(config, str) or config is None:
            self._config = load_config(config)
        else:
            self._config = config

        self._rag = RagService(self._config)
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        # 启动 LLM 后台服务
        print("[worker] starting LLM backend...", flush=True)
        self._rag.llm_launcher.start()
        print("[worker] LLM backend ready", flush=True)

    async def handle_task(
        self,
        task_id: str,
        request: dict[str, Any],
        send_event: Callable[[str, dict[str, Any] | None], Coroutine[Any, Any, None]],
    ) -> None:
        """执行 RAG Pipeline 并将所有事件通过 `send_event` 回调发送。

        Args:
            task_id: 任务 ID（用于取消关联）。
            request: 任务请求，包含 messages, conversation_id, identity_id。
            send_event: 异步回调 `async def send_event(event_type, data)`。
        """
        # 创建取消事件
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[task_id] = cancel_event

        try:
            messages = request.get("messages", [])
            if not messages:
                await send_event(
                    "error",
                    {"code": "bad_request", "message": "no messages in request"},
                )
                await send_event(
                    "done",
                    {"finish_reason": "error", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
                )
                return

            # 发送开始事件
            await send_event("start", {"task_id": task_id})

            # 调用 RagService.answer_stream（同步迭代器）
            # 在专用线程中运行同步生成器，通过回调发送事件
            loop = None
            try:
                import asyncio
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            def _run_sync() -> None:
                """在线程中运行同步生成器，通过回调发送事件。"""
                try:
                    for event_type, data in self._rag.answer_stream(
                        messages, cancel_event=cancel_event
                    ):
                        if cancel_event.is_set():
                            # 取消 — 在回调中发送取消事件
                            if loop is not None:
                                asyncio.run_coroutine_threadsafe(
                                    send_event(
                                        "error",
                                        {"code": "cancelled", "message": "generation cancelled"},
                                    ),
                                    loop,
                                )
                                asyncio.run_coroutine_threadsafe(
                                    send_event(
                                        "done",
                                        {
                                            "finish_reason": "cancelled",
                                            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                                        },
                                    ),
                                    loop,
                                )
                            return

                        # 将事件数据转为可序列化的格式
                        if event_type == "reference":
                            # data 是 list[RetrievedChunk]
                            items = []
                            for chunk in data:
                                items.append(
                                    {
                                        "title": str(chunk.metadata.get("title") or "Untitled"),
                                        "url": str(chunk.metadata.get("source_url") or ""),
                                        "snippet": (
                                            chunk.text[:400]
                                            if len(chunk.text) > 400
                                            else chunk.text
                                        ),
                                        "score": float(chunk.score),
                                        "source": str(chunk.metadata.get("source") or ""),
                                    }
                                )
                            payload = {"items": items}
                        elif event_type in ("think.delta", "content.delta"):
                            payload = {"text": data}
                        elif event_type == "think.end":
                            payload = {}
                        else:
                            # retrieval.decision, retrieval.assessment, support.decision 等
                            payload = data if isinstance(data, dict) else {"data": data}

                        if loop is not None:
                            asyncio.run_coroutine_threadsafe(
                                send_event(event_type, payload), loop
                            )

                    # 正常完成
                    if loop is not None and not cancel_event.is_set():
                        asyncio.run_coroutine_threadsafe(
                            send_event(
                                "done",
                                {
                                    "finish_reason": "stop",
                                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                                },
                            ),
                            loop,
                        )

                except GenerationCancelledError:
                    if loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            send_event(
                                "error",
                                {"code": "cancelled", "message": "generation cancelled"},
                            ),
                            loop,
                        )
                        asyncio.run_coroutine_threadsafe(
                            send_event(
                                "done",
                                {
                                    "finish_reason": "cancelled",
                                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                                },
                            ),
                            loop,
                        )
                except Exception:
                    traceback.print_exc()
                    if loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            send_event(
                                "error",
                                {"code": "server_error", "message": traceback.format_exc()},
                            ),
                            loop,
                        )
                        asyncio.run_coroutine_threadsafe(
                            send_event(
                                "done",
                                {
                                    "finish_reason": "error",
                                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                                },
                            ),
                            loop,
                        )

            # 在线程池中运行同步生成器
            if loop is not None:
                await loop.run_in_executor(None, _run_sync)
            else:
                _run_sync()

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
            with self._lock:
                self._cancel_events.pop(task_id, None)

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务。返回 True 表示成功触发取消。"""
        with self._lock:
            event = self._cancel_events.get(task_id)
            if event is None:
                return False
            event.set()
            return True

    def health_check(self) -> dict[str, Any]:
        """执行健康检查。"""
        return self._rag.health_check()