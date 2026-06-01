from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """统一的生成接口；不负责进程生命周期。"""

    def generate(self, prompt: str) -> str:
        """执行一次非流式文本生成。"""

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, str]]:
        """执行一次流式生成；cancel_event 用于主动中止底层请求。"""


class LLMLauncher(Protocol):
    """负责托管式后端的校验、启动和关闭。"""

    def verify(self) -> tuple[bool, str]:
        """检查当前后端配置与依赖是否可用。"""

    def start(self) -> None:
        """启动后端服务并等待其就绪。"""

    def shutdown(self) -> None:
        """释放后端持有的进程、连接或设备资源。"""


@dataclass(frozen=True)
class LLMRuntime:
    client: LLMClient
    launcher: LLMLauncher


class LLMBackend(Protocol):
    """临时兼容旧调用点；重构完成后会移除。"""

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
