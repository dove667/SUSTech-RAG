from __future__ import annotations

import json
from typing import Any


def sse_frame(event: str, data: dict[str, Any]) -> str:
    """One SSE message: event line + data line + blank line (RFC)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
