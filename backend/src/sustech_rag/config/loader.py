from __future__ import annotations

from pathlib import Path

import yaml

from sustech_rag.config.models import AppConfig, LlamaCppConfig, VLLMConfig


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


def _resolve_path_value(raw_path: str, project_root: Path) -> str:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((project_root / path).resolve())


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
    data_dir = Path(_resolve_path_value(str(config.project.data_dir), project_root))
    config.project.data_dir = data_dir
    config.vector_store.persist_dir = Path(
        _resolve_path_value(str(config.vector_store.persist_dir), project_root)
    )
    if config.embedding.local_path:
        config.embedding.local_path = _resolve_path_value(config.embedding.local_path, project_root)
    if config.retrieval.reranker_local_path:
        config.retrieval.reranker_local_path = _resolve_path_value(
            config.retrieval.reranker_local_path,
            project_root,
        )
    if isinstance(config.llm, LlamaCppConfig) and config.llm.model_path:
        config.llm.model_path = _resolve_path_value(config.llm.model_path, project_root)
    if isinstance(config.llm, VLLMConfig):
        if config.llm.local_path:
            config.llm.local_path = _resolve_path_value(config.llm.local_path, project_root)
        if config.llm.binary_path:
            config.llm.binary_path = _resolve_path_value(config.llm.binary_path, project_root)
    return config
