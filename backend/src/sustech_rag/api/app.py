from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sustech_rag.api.routes import http_error_handler, router
from sustech_rag.config.loader import load_config
from sustech_rag.pipeline.rag_service import RagService


def _initial_config_path() -> str | None:
    raw = os.environ.get("SUSTECH_RAG_CONFIG", "").strip()
    return raw or None


def create_app(config_path: str | None = None) -> FastAPI:
    """
    Build FastAPI app. If ``config_path`` is None, uses env ``SUSTECH_RAG_CONFIG`` or default YAML.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        path = config_path if config_path is not None else _initial_config_path()
        print("[sustech-rag] loading config...", flush=True)
        cfg = load_config(path)
        app.state.app_config = cfg
        print(
            "[sustech-rag] loading RAG (embedding + Chroma + reranker; first run may take minutes)...",
            flush=True,
        )
        try:
            app.state.rag = RagService(cfg)
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
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://frp-off.com:35380",
            "http://60.215.128.117:35380",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


# Uvicorn default import target; set ``SUSTECH_RAG_CONFIG`` before load if needed.
app = create_app()


def run_dev_server(host: str = "0.0.0.0", port: int = 8000, config_path: str | None = None) -> None:
    """Run with in-process app instance (used by CLI ``serve``)."""
    import uvicorn

    print(
        f"[sustech-rag] starting uvicorn on http://{host}:{port} "
        "(HTTP logs appear after startup completes).\n",
        flush=True,
    )
    cfg_path = config_path
    if cfg_path is None:
        cfg_path = _initial_config_path()
    application = create_app(cfg_path)
    uvicorn.run(application, host=host, port=port, log_level="info")
