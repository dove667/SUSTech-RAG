from __future__ import annotations

import os
from pathlib import Path

from sustech_rag.utils.io import ensure_dir


def prepare_model_cache(base_dir: Path) -> Path:
    cache_dir = ensure_dir(base_dir / "cache" / "huggingface")
    os.environ.setdefault("HF_HOME", str(cache_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_dir / "transformers"))
    return cache_dir
