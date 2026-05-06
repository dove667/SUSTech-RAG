from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from sustech_rag.api.schemas import (
    ChatCancelRequest,
    ChatCompletionRequest,
    IdentityResponse,
    KnowledgeBaseItem,
    KnowledgeBasesResponse,
)
from sustech_rag.api.sse import sse_frame
from sustech_rag.pipeline.rag_service import RagService
from sustech_rag.retrieval.reranker import RetrievedChunk

router = APIRouter(tags=["chat"])

# 取消令牌注册表：key = "{identity_id}:{message_id}" → threading.Event
_cancel_tokens: dict[str, threading.Event] = {}


def get_rag(request: Request) -> RagService:
    rag = getattr(request.app.state, "rag", None)
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "server_error", "message": "RAG service not ready"},
        )
    ready = getattr(request.app.state, "ready", False)
    if not ready:
        raise HTTPException(
            status_code=503,
            detail={"code": "server_error", "message": "RAG components not ready"},
        )
    return rag


def get_identity_id(request: Request) -> str:
    """从 X-Identity-ID 请求头提取身份 ID，写入 request.state。缺省返回空字符串。"""
    identity_id = request.headers.get("X-Identity-ID", "").strip()
    request.state.identity_id = identity_id
    return identity_id


def _chunks_to_reference_items(chunks: list[RetrievedChunk], snippet_max: int = 400) -> list[dict]:
    items: list[dict] = []
    for ch in chunks:
        title = str(ch.metadata.get("title") or "Untitled")
        url = str(ch.metadata.get("source_url") or "")
        snippet = ch.text[:snippet_max] if len(ch.text) > snippet_max else ch.text
        items.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "score": float(ch.score),
            }
        )
    return items


def _sync_stream(
    messages: list,
    rag: RagService,
    conversation_id: str,
    message_id: str,
    identity_id: str,
) -> Iterator[str]:
    """同步 SSE 生成器：直接在迭代循环中检查取消令牌，无需 async/线程/队列。"""
    yield sse_frame("start", {"conversation_id": conversation_id, "message_id": message_id})

    token_key = f"{identity_id}:{message_id}"
    cancel_event = threading.Event()
    _cancel_tokens[token_key] = cancel_event

    api_messages = [{"role": m.role, "content": m.content} for m in messages]

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
                yield sse_frame("reference", {"items": _chunks_to_reference_items(data)})
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


async def _async_stream(sync_iter: Iterator[str]) -> AsyncIterator[str]:
    """Wrap the synchronous SSE generator so next() runs in a thread executor.

    Starlette wraps sync iterators in ``anyio.to_thread.run_sync``, which
    pushes *every* yield through a thread-pool round-trip.  By providing an
    async generator we let Starlette iterate us directly on the event loop.
    """
    loop = asyncio.get_running_loop()
    it = iter(sync_iter)
    _SENTINEL = object()

    def _next() -> str | object:
        """Catch StopIteration inside the thread — Python 3.11+ asyncio
        cannot raise StopIteration into a Future (it interacts badly
        with generators)."""
        try:
            return next(it)
        except StopIteration:
            return _SENTINEL

    while True:
        item = await loop.run_in_executor(None, _next)
        if item is _SENTINEL:
            break
        yield item


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health")
def health(request: Request) -> JSONResponse:
    rag = getattr(request.app.state, "rag", None)
    ready = getattr(request.app.state, "ready", False)
    startup_error = getattr(request.app.state, "startup_error", "")
    if rag is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": startup_error or "RAG service init failed",
                "components": {},
            },
        )
    if not ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": startup_error or "components not ready",
                "components": {},
            },
        )
    health = rag.health_check()
    status_code = 200 if health["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=health)


@router.post("/identity")
def assign_identity() -> IdentityResponse:
    """分配一个新的身份 ID。前端首次加载时调用，之后持久化复用。"""
    return IdentityResponse(identity_id=uuid.uuid4().hex)


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    rag: Annotated[RagService, Depends(get_rag)],
    _identity: Annotated[str, Depends(get_identity_id)],
) -> Response:
    if not body.stream:
        return JSONResponse(
            status_code=400,
            content={"code": "bad_request", "message": "stream must be true"},
        )

    conversation_id = body.conversation_id or f"c_{uuid.uuid4().hex[:16]}"
    message_id = f"m_{uuid.uuid4().hex[:16]}"
    identity_id = getattr(request.state, "identity_id", "")

    return StreamingResponse(
        _async_stream(
            _sync_stream(body.messages, rag, conversation_id, message_id, identity_id)
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/cancel")
def chat_cancel(
    body: ChatCancelRequest,
    request: Request,
    _identity: Annotated[str, Depends(get_identity_id)],
) -> JSONResponse:
    identity_id = getattr(request.state, "identity_id", "")
    token_key = f"{identity_id}:{body.message_id}"
    event = _cancel_tokens.get(token_key)
    if event is None:
        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": "no active generation to cancel"},
        )
    event.set()
    return JSONResponse(content={"code": "cancelled", "message": "ok"})


@router.get("/knowledge_bases")
def knowledge_bases(
    request: Request,
    _identity: Annotated[str, Depends(get_identity_id)],
) -> KnowledgeBasesResponse:
    cfg = getattr(request.app.state, "app_config", None)
    coll = cfg.vector_store.collection_name if cfg is not None else ""
    name = f"默认库（{coll}）" if coll else "默认库"
    # query actual doc count from Chroma
    try:
        from sustech_rag.utils.chroma_client import persistent_client

        client = persistent_client(str(cfg.vector_store.persist_dir))
        collection = client.get_collection(coll)
        count = collection.count()
    except Exception:
        count = 0
    item = KnowledgeBaseItem(id="kb_default", name=name, doc_count=count)
    return KnowledgeBasesResponse(items=[item])


def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "bad_request", "message": detail.get("message", str(detail))},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "bad_request", "message": str(detail)},
    )
