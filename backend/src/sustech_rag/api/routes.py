from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from sustech_rag.api.schemas import (
    CancelResponse,
    ChatCancelRequest,
    ChatCompletionRequest,
    ErrorResponse,
    HealthResponse,
    IdentityResponse,
    KnowledgeBaseItem,
    KnowledgeBasesResponse,
)
from sustech_rag.api.sse import sse_frame
from sustech_rag.pipeline.rag_service import RagService
from sustech_rag.retrieval.reranker import RetrievedChunk

router = APIRouter(tags=["对话接口"])

# 取消令牌注册表：key = "{identity_id}:{message_id}" → threading.Event
_cancel_tokens: dict[str, threading.Event] = {}


def get_rag(request: Request) -> RagService:
    rag = getattr(request.app.state, "rag", None)
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                code="server_error",
                message="RAG service not ready",
            ).model_dump(),
        )
    ready = getattr(request.app.state, "ready", False)
    if not ready:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                code="server_error",
                message="RAG components not ready",
            ).model_dump(),
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
    """包装同步 SSE 生成器，让 `next()` 在线程执行器中运行。

    Starlette 会把同步迭代器包装进 `anyio.to_thread.run_sync`，
    使每次 `yield` 都经历一次线程池往返。这里显式提供异步生成器，
    让 Starlette 直接在事件循环中迭代，减少额外调度开销。
    """
    loop = asyncio.get_running_loop()
    it = iter(sync_iter)
    _SENTINEL = object()

    def _next() -> str | object:
        """在线程内吞掉 StopIteration，避免它穿透到 Future。"""
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
# 路由定义
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="健康检查",
    response_model=HealthResponse,
    response_description="后端健康状态。",
    responses={503: {"model": HealthResponse, "description": "服务未就绪或启动失败。"}},
)
def health(request: Request) -> JSONResponse:
    """返回后端健康状态和组件就绪情况。"""
    rag = getattr(request.app.state, "rag", None)
    ready = getattr(request.app.state, "ready", False)
    startup_error = getattr(request.app.state, "startup_error", "")
    if rag is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(
                status="error",
                message=startup_error or "RAG service init failed",
                components={},
            ).model_dump(),
        )
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(
                status="error",
                message=startup_error or "components not ready",
                components={},
            ).model_dump(),
        )
    health = HealthResponse.model_validate(rag.health_check())
    status_code = (
        status.HTTP_200_OK
        if health.status == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=health.model_dump(exclude_none=True))


@router.post(
    "/identity",
    summary="分配身份 ID",
    response_model=IdentityResponse,
    response_description="新分配的浏览器身份 ID。",
)
def assign_identity() -> IdentityResponse:
    """分配一个新的身份 ID。前端首次加载时调用，之后持久化复用。"""
    return IdentityResponse(identity_id=uuid.uuid4().hex)


@router.post(
    "/chat/completions",
    summary="流式问答",
    response_description="SSE 事件流，事件类型包括 start、reference、think.delta、think.end、content.delta、error、done。",
    responses={
        200: {
            "description": "SSE 流式输出。",
            "content": {
                "text/event-stream": {
                    "example": (
                        "event: start\n"
                        'data: {"conversation_id":"c_demo_001","message_id":"m_demo_001"}\n\n'
                    )
                }
            },
        },
        400: {"model": ErrorResponse, "description": "请求参数不合法。"},
        503: {"model": ErrorResponse, "description": "RAG 服务未就绪。"},
    },
)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    rag: Annotated[RagService, Depends(get_rag)],
    _identity: Annotated[str, Depends(get_identity_id)],
) -> Response:
    """基于对话消息生成 SSE 流式回答。当前仅支持 `stream=true`。"""
    if not body.stream:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                code="bad_request",
                message="stream must be true",
            ).model_dump(),
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


@router.post(
    "/chat/cancel",
    summary="取消生成",
    response_model=CancelResponse,
    response_description="取消请求处理结果。",
    responses={
        404: {"model": ErrorResponse, "description": "未找到可取消的活跃生成任务。"},
    },
)
def chat_cancel(
    body: ChatCancelRequest,
    request: Request,
    _identity: Annotated[str, Depends(get_identity_id)],
) -> JSONResponse:
    """取消指定身份下正在进行的流式生成。"""
    identity_id = getattr(request.state, "identity_id", "")
    token_key = f"{identity_id}:{body.message_id}"
    event = _cancel_tokens.get(token_key)
    if event is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                code="not_found",
                message="no active generation to cancel",
            ).model_dump(),
        )
    event.set()
    return JSONResponse(content=CancelResponse(code="cancelled", message="ok").model_dump())


@router.get(
    "/knowledge_bases",
    summary="列出知识库",
    response_model=KnowledgeBasesResponse,
    response_description="当前可用知识库列表。",
)
def knowledge_bases(
    request: Request,
    _identity: Annotated[str, Depends(get_identity_id)],
) -> KnowledgeBasesResponse:
    """返回当前服务暴露的知识库信息。"""
    cfg = getattr(request.app.state, "app_config", None)
    coll = cfg.vector_store.collection_name if cfg is not None else ""
    name = f"默认库（{coll}）" if coll else "默认库"
    # 从 Chroma 查询实际文档数；失败时降级为 0，避免影响接口可用性。
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
