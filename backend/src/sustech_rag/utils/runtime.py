from __future__ import annotations

import os
import shutil
from pathlib import Path

from sustech_rag.utils.io import ensure_dir
from sustech_rag.utils.platform import default_llama_binary_name


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


def ensure_llama_cpp_binary() -> str:
    """Ensure *llama-server* is available on PATH."""
    binary_name = default_llama_binary_name()
    resolved = shutil.which(binary_name)
    if resolved:
        print(f"[sustech-rag] llama.cpp binary found on PATH: {resolved}", flush=True)
        return resolved

    raise FileNotFoundError(
        f"llama-server binary not found on PATH: {binary_name}\n"
        "Install llama.cpp and make llama-server available on PATH."
    )


def ensure_gguf_model(model_path: str) -> str:
    path = Path(model_path)
    if path.exists():
        return str(path)

    raise FileNotFoundError(
        f"GGUF model not found: {model_path}\n"
        "Run uv run sustech-rag download-model or set llm.model_path "
        "to an existing GGUF file."
    )
