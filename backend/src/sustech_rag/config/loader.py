from __future__ import annotations

from pathlib import Path

import yaml

from sustech_rag.config.models import AppConfig


def resolve_config_path(config_path: str | None = None) -> Path:
    """
    解析配置文件路径，支持显式路径和默认路径。
    输入参数：
    - config_path：外部传入的配置文件路径，可为空。
    输出参数：
    - Path：解析后的绝对配置文件路径。
    """

    raw = config_path or "configs/default.yaml"
    return Path(raw).expanduser().resolve()


def load_config(config_path: str | None = None) -> AppConfig:
    """
    加载 YAML 配置并转换为应用配置模型，同时修正相对路径。
    输入参数：
    - config_path：外部传入的配置文件路径，可为空。
    输出参数：
    - AppConfig：返回已解析并完成路径修正的应用配置对象。
    """

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
        config.retrieval.reranker_local_path = str(
            (project_root / config.retrieval.reranker_local_path).resolve()
        )
    if config.llm.model_path:
        config.llm.model_path = str((project_root / config.llm.model_path).resolve())
    return config
