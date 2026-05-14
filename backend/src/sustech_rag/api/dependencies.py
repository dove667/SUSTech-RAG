from __future__ import annotations

from fastapi import HTTPException, Request, status

from sustech_rag.api.schemas import ErrorResponse
from sustech_rag.pipeline.rag_service import RagService


def get_rag(request: Request) -> RagService:
    rag = getattr(request.app.state, "rag", None)
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                code="service_unavailable",
                message="RAG service not ready",
            ).model_dump(),
        )

    ready = getattr(request.app.state, "ready", False)
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                code="service_unavailable",
                message="RAG components not ready",
            ).model_dump(),
        )

    return rag


def get_identity_id(request: Request) -> str:
    """从 X-Identity-ID 请求头提取身份 ID，写入 request.state。缺省返回空字符串。"""
    identity_id = request.headers.get("X-Identity-ID", "").strip()
    request.state.identity_id = identity_id
    return identity_id
