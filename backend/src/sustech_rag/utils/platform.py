from __future__ import annotations

import platform
from pathlib import Path


def is_windows() -> bool:
    """
    判断当前运行环境是否为 Windows。
    输入参数：无。
    输出参数：当前平台为 Windows 时返回 True，否则返回 False。
    """
    return platform.system().lower() == "windows"


def default_llama_binary_name() -> str:
    """
    根据当前平台返回默认的 llama.cpp 可执行文件名。
    输入参数：无。
    输出参数：Windows 返回 "llama-cli.exe"，其他平台返回 "llama-cli"。
    """
    return "llama-cli.exe" if is_windows() else "llama-cli"


def normalize_path(raw: str | Path) -> Path:
    """
    将输入路径规范化为绝对路径并展开用户目录。
    输入参数：raw，待规范化的字符串路径或 Path 对象。
    输出参数：规范化后的 Path 对象。
    """
    return Path(raw).expanduser().resolve()
