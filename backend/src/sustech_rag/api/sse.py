from __future__ import annotations

import json
from typing import Any


def sse_frame(event: str, data: dict[str, Any]) -> str:
    """构造一条 SSE 消息：事件行 + 数据行 + 空行。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
