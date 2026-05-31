from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Protocol


class LLMBackend(Protocol):
    """公共 LLM backend 接口，便于后续切换到 vLLM 等实现。"""

    def start(self) -> None:
        """启动后端服务或完成必要预热。"""

    def shutdown(self) -> None:
        """释放后端持有的进程、连接或设备资源。"""

    def verify(self) -> tuple[bool, str]:
        """检查当前后端配置与依赖是否可用。"""

    def generate(self, prompt: str) -> str:
        """执行一次非流式文本生成。"""

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, str]]:
        """执行一次流式生成；cancel_event 用于主动中止底层请求。"""
