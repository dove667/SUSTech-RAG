from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """
    确保目标目录存在，不存在则递归创建。
    输入参数：path，需要创建或确认存在的目录路径。
    输出参数：原始 Path 对象。
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    """
    将字典迭代写入 JSONL 文件。
    输入参数：path，目标 JSONL 文件路径；rows，需要写入的字典迭代对象。
    输出参数：无。
    """
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """
    读取 JSONL 文件并解析为字典列表。
    输入参数：path，目标 JSONL 文件路径。
    输出参数：解析后的字典列表；文件不存在时返回空列表。
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
