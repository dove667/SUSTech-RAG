from __future__ import annotations

import os
from pathlib import Path

from sustech_rag.utils.io import ensure_dir


def prepare_model_cache(base_dir: Path) -> Path:
    cache_dir = ensure_dir(base_dir / "cache" / "huggingface")
    os.environ.setdefault("HF_HOME", str(cache_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_dir / "transformers"))
    llama_index_cache = ensure_dir(base_dir / "cache" / "llama_index")
    os.environ.setdefault("XDG_CACHE_HOME", str(base_dir / "cache"))
    os.environ.setdefault("LLAMA_INDEX_CACHE_DIR", str(llama_index_cache))
    return cache_dir
