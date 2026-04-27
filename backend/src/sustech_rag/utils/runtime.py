from __future__ import annotations

from pathlib import Path

from sustech_rag.utils.io import ensure_dir


def prepare_model_cache(base_dir: Path) -> Path:
    """
    初始化模型相关缓存目录。
    输入参数：base_dir，缓存根目录。
    输出参数：HuggingFace 缓存目录 Path 对象。
    """
    cache_dir = ensure_dir(base_dir / "cache" / "huggingface")
    ensure_dir(cache_dir / "hub")
    ensure_dir(cache_dir / "transformers")
    ensure_dir(base_dir / "cache" / "llama_index")
    return cache_dir
