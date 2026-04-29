from __future__ import annotations

import os
from pathlib import Path

from sustech_rag.utils.io import ensure_dir


def prepare_model_cache(base_dir: Path) -> Path:
    """
    初始化模型目录并设置 HuggingFace 运行时环境变量。
    输入参数：base_dir，数据根目录。
    输出参数：HuggingFace 模型目录 Path 对象。
    """
    model_dir = ensure_dir(base_dir / "models" / ".cache")
    os.environ.setdefault("HF_HOME", str(model_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(model_dir / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(model_dir / "transformers"))
    return model_dir
