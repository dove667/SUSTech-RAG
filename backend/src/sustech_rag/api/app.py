from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sustech_rag.api.routes import http_error_handler, router
from sustech_rag.config.models import AppConfig
from sustech_rag.pipeline.rag_service import RagService


def _cors_origins() -> list[str]:
    """CORS allowed origins — localhost defaults + optional env override."""
    defaults = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    extra = os.environ.get("SUSTECH_RAG_CORS_ORIGINS", "").strip()
    if extra:
        defaults.extend(origin.strip() for origin in extra.split(",") if origin.strip())
    return defaults


def create_app(config: AppConfig) -> FastAPI:
    """Build FastAPI app from an already-loaded config."""

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

        # hot-load the LLM model (keeps the process alive for all requests)
        app.state.rag.llm.start()
        app.state.ready = True
        print("[sustech-rag] all components ready; serving requests.", flush=True)
        yield
        # shutdown: kill the persistent llama-server process
        app.state.rag.llm.shutdown()

    app = FastAPI(title="SUSTech Campus RAG API", lifespan=lifespan)
    app.add_exception_handler(HTTPException, http_error_handler)
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
    """Run with in-process app instance (used by CLI ``serve``)."""
    import uvicorn

    print(
        f"[sustech-rag] starting uvicorn on http://{host}:{port} "
        "(HTTP logs appear after startup completes).\n",
        flush=True,
    )
    application = create_app(config)
    uvicorn.run(application, host=host, port=port, log_level="info")
