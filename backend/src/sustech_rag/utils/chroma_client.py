from __future__ import annotations

import chromadb
from chromadb.config import Settings


def persistent_client(persist_dir: str) -> chromadb.PersistentClient:
    """
    Chroma 持久化客户端；关闭匿名遥测，避免与 posthog>=6 的 API 不兼容导致日志报错。
    """
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
