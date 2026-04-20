from __future__ import annotations

import os
from pathlib import Path

import yaml

from sustech_rag.config.models import AppConfig


def resolve_config_path(config_path: str | None = None) -> Path:
    raw = config_path or os.getenv("SUSTECH_RAG_CONFIG") or "configs/default.yaml"
    return Path(raw).expanduser().resolve()


def load_config(config_path: str | None = None) -> AppConfig:
    path = resolve_config_path(config_path)
    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh)
    config = AppConfig.model_validate(payload)
    project_root = path.parent.parent
    data_dir = (project_root / config.project.data_dir).resolve()
    config.project.data_dir = data_dir
    config.vector_store.persist_dir = (project_root / config.vector_store.persist_dir).resolve()
    if config.embedding.local_path:
        config.embedding.local_path = str((project_root / config.embedding.local_path).resolve())
    if config.retrieval.reranker_local_path:
        config.retrieval.reranker_local_path = str((project_root / config.retrieval.reranker_local_path).resolve())
    if config.llm.local.binary_path:
        config.llm.local.binary_path = str((project_root / config.llm.local.binary_path).resolve())
    if config.llm.local.model_path:
        config.llm.local.model_path = str((project_root / config.llm.local.model_path).resolve())
    return config
