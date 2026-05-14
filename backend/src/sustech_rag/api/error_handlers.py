from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from sustech_rag.api.schemas import ErrorResponse


def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
    print(f"[sustech-rag] unhandled exception: {exc}", flush=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code="internal_server_error",
            message="internal server error",
        ).model_dump(),
    )
