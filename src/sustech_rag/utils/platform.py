from __future__ import annotations

import platform
from pathlib import Path


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def default_llama_binary_name() -> str:
    return "llama-cli.exe" if is_windows() else "llama-cli"


def normalize_path(raw: str | Path) -> Path:
    return Path(raw).expanduser().resolve()
