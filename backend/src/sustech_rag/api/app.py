from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sustech_rag.api.routes import internal_error_handler, router
from sustech_rag.config.models import AppConfig
from sustech_rag.pipeline.rag_service import RagService


def _cors_origins() -> list[str]:
    """返回允许的 CORS 来源，默认包含本地开发地址，并支持环境变量追加。"""
    defaults = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    extra = os.environ.get("SUSTECH_RAG_CORS_ORIGINS", "").strip()
    if extra:
        defaults.extend(origin.strip() for origin in extra.split(",") if origin.strip())
    return defaults


def create_app(config: AppConfig) -> FastAPI:
    """根据已加载配置构建 FastAPI 应用。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        print("[sustech-rag] loading config...", flush=True)
        app.state.app_config = config
        print(
            "[sustech-rag] loading RAG "
            "(embedding + Chroma + reranker; first run may take minutes)...",
            flush=True,
        )
        try:
            app.state.rag = RagService(config)
        except Exception as exc:
            msg = f"RAG service init failed: {exc}"
            print(f"[sustech-rag] FATAL: {msg}", flush=True)
            raise RuntimeError(msg) from exc

        print("[sustech-rag] running health checks...", flush=True)
        health = app.state.rag.health_check()
        if health["status"] != "ready":
            app.state.ready = False
            msg = f"Startup health check failed: {health['components']}"
            print(f"[sustech-rag] ERROR: {msg}", flush=True)
            raise RuntimeError(msg)

        # 预热并常驻启动 LLM，供后续请求复用。
        app.state.rag.llm.start()
        app.state.ready = True
        print("[sustech-rag] all components ready; serving requests.", flush=True)
        yield
        # 关闭时回收常驻的 llama-server 进程。
        app.state.rag.llm.shutdown()

    app = FastAPI(
        title="SUSTech Campus RAG API",
        summary="南方科技大学校园知识库问答后端接口",
        description=(
            "提供身份分配、知识库查询、健康检查以及基于 SSE 的流式问答接口。"
            "当前聊天接口要求 `stream=true`，并通过 `X-Identity-ID` 请求头关联浏览器身份。"
        ),
        version="0.1.0",
        openapi_tags=[
            {
                "name": "对话接口",
                "description": "聊天、取消生成、身份分配、知识库和健康检查相关接口。",
            }
        ],
        lifespan=lifespan,
    )
    app.add_exception_handler(Exception, internal_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


def run_dev_server(
    config: AppConfig,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """使用当前进程内的应用实例启动开发服务器，供 CLI `serve` 调用。"""
    import uvicorn

    print(
        f"[sustech-rag] starting uvicorn on http://{host}:{port} "
        "(HTTP logs appear after startup completes).\n",
        flush=True,
    )
    application = create_app(config)
    uvicorn.run(application, host=host, port=port, log_level="info")
