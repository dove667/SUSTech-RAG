from __future__ import annotations

import json
import asyncio
import threading
from collections.abc import AsyncIterator, Iterator
from typing import Any

from sustech_rag.pipeline.rag_service import RagService
from sustech_rag.retrieval.reranker import RetrievedChunk

# 取消令牌注册表：key = "{identity_id}:{message_id}" → threading.Event
_cancel_tokens: dict[str, threading.Event] = {}


def sse_frame(event: str, data: dict[str, Any]) -> str:
    """构造一条 SSE 消息：事件行 + 数据行 + 空行。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _cancel_token_key(identity_id: str, message_id: str) -> str:
    return f"{identity_id}:{message_id}"


def cancel_generation(identity_id: str, message_id: str) -> bool:
    event = _cancel_tokens.get(_cancel_token_key(identity_id, message_id))
    if event is None:
        return False
    event.set()
    return True


def chunks_to_reference_items(
    chunks: list[RetrievedChunk], snippet_max: int = 400
) -> list[dict[str, str | float]]:
    items: list[dict[str, str | float]] = []
    for chunk in chunks:
        title = str(chunk.metadata.get("title") or "Untitled")
        url = str(chunk.metadata.get("source_url") or "")
        snippet = chunk.text[:snippet_max] if len(chunk.text) > snippet_max else chunk.text
        items.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "score": float(chunk.score),
            }
        )
    return items


def sync_chat_stream(
    messages: list,
    rag: RagService,
    conversation_id: str,
    message_id: str,
    identity_id: str,
) -> Iterator[str]:
    """同步 SSE 生成器：直接在迭代循环中检查取消令牌，无需 async/线程/队列。"""
    yield sse_frame("start", {"conversation_id": conversation_id, "message_id": message_id})

    token_key = _cancel_token_key(identity_id, message_id)
    cancel_event = threading.Event()
    _cancel_tokens[token_key] = cancel_event

    api_messages = [{"role": message.role, "content": message.content} for message in messages]

    try:
        for event_type, data in rag.answer_stream(api_messages):
            if cancel_event.is_set():
                yield sse_frame("error", {"code": "cancelled", "message": "generation cancelled"})
                yield sse_frame(
                    "done",
                    {
                        "finish_reason": "cancelled",
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    },
                )
                return
            if event_type == "reference":
                yield sse_frame("reference", {"items": chunks_to_reference_items(data)})
            elif event_type == "think.delta":
                yield sse_frame("think.delta", {"text": data})
            elif event_type == "think.end":
                yield sse_frame("think.end", {})
            elif event_type == "content.delta":
                yield sse_frame("content.delta", {"text": data})

        yield sse_frame(
            "done",
            {"finish_reason": "stop", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
        )
    except Exception as exc:
        yield sse_frame("error", {"code": "server_error", "message": str(exc)})
        yield sse_frame(
            "done",
            {"finish_reason": "error", "usage": {"prompt_tokens": 0, "completion_tokens": 0}},
        )
    finally:
        _cancel_tokens.pop(token_key, None)


async def async_chat_stream(sync_iter: Iterator[str]) -> AsyncIterator[str]:
    """
    包装同步 SSE 生成器，把 `next()` 扔到线程池中运行。
    Starlette 会把同步迭代器包装进 `anyio.to_thread.run_sync`，
    使每次 `yield` 都经历一次线程池往返。这里显式提供异步生成器，
    让 Starlette 直接在事件循环中迭代，减少额外调度开销。
    """
    loop = asyncio.get_running_loop()
    iterator = iter(sync_iter)
    sentinel = object()

    def _next() -> str | object:
        """
        StopIteration 不能作为 Future 的异常。
        在线程内吞掉 StopIteration，避免它穿透到 Future。
        """
        try:
            return next(iterator)
        except StopIteration:
            return sentinel

    while True:
        item = await loop.run_in_executor(None, _next)
        if item is sentinel:
            break
        yield item
