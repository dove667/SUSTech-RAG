from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from sustech_rag.api.chat_stream import async_chat_stream, cancel_generation, sync_chat_stream
from sustech_rag.api.dependencies import get_identity_id, get_rag
from sustech_rag.api.schemas import (
    CancelResponse,
    ChatCancelRequest,
    ChatCompletionRequest,
    ErrorResponse,
    HealthResponse,
    IdentityResponse,
)
from sustech_rag.pipeline.rag_service import RagService

router = APIRouter(tags=["对话接口"])


@router.get(
    "/health",
    summary="健康检查",
    response_model=HealthResponse,
    response_description="后端健康状态。",
    responses={503: {"model": HealthResponse, "description": "服务未就绪或启动失败。"}},
)
def health(request: Request, response: Response) -> HealthResponse:
    """返回后端健康状态和组件就绪情况。"""
    rag = getattr(request.app.state, "rag", None)
    ready = getattr(request.app.state, "ready", False)
    startup_error = getattr(request.app.state, "startup_error", "")
    if rag is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="error",
            message=startup_error or "RAG service init failed",
            components={},
        )
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="error",
            message=startup_error or "components not ready",
            components={},
        )
    health = HealthResponse.model_validate(rag.health_check())
    if health.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health


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
    response_description=(
        "SSE 事件流，事件类型包括 start、reference、think.delta、"
        "think.end、content.delta、error、done。"
    ),
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
    response: Response,
    rag: Annotated[RagService, Depends(get_rag)],
    _identity: Annotated[str, Depends(get_identity_id)],
) -> Response:
    """基于对话消息生成 SSE 流式回答。当前仅支持 `stream=true`。"""
    if not body.stream:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ErrorResponse(
            code="bad_request",
            message="stream must be true",
        )

    conversation_id = body.conversation_id or f"c_{uuid.uuid4().hex[:16]}"
    message_id = f"m_{uuid.uuid4().hex[:16]}"
    identity_id = getattr(request.state, "identity_id", "")

    return StreamingResponse(
        async_chat_stream(
            sync_chat_stream(body.messages, rag, conversation_id, message_id, identity_id)
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
    response_model=CancelResponse | ErrorResponse,
    response_description="取消请求处理结果。",
    responses={
        404: {"model": ErrorResponse, "description": "未找到可取消的活跃生成任务。"},
    },
)
def chat_cancel(
    body: ChatCancelRequest,
    request: Request,
    _identity: Annotated[str, Depends(get_identity_id)],
    response: Response,
) -> CancelResponse | ErrorResponse:
    """取消指定身份下正在进行的流式生成。"""
    identity_id = getattr(request.state, "identity_id", "")
    if not cancel_generation(identity_id, body.message_id):
        response.status_code = status.HTTP_404_NOT_FOUND
        return ErrorResponse(
            code="not_found",
            message="no active generation to cancel",
        )
    return CancelResponse(code="cancelled", message="ok")
