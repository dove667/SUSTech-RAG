from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class OpenAICompatibleEndpoint:
    host: str
    port: int
    model_path: str
    served_model_name: str = ""
    api_key: str = ""

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LLMClient(Protocol):
    """统一的生成接口；不负责进程生命周期。"""

    def generate(self, messages: list[dict]) -> str:
        """执行一次非流式生成。"""

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, str]]:
        """执行一次流式生成；cancel_event 用于主动中止底层请求。"""


class OpenAICompatibleClientBase(ABC):
    """共享 OpenAI-compatible 推理端点的请求与流式解析逻辑。"""

    def __init__(
        self,
        endpoint: OpenAICompatibleEndpoint,
        temperature: float,
        max_tokens: int,
        stop: list[str],
    ) -> None:
        self._endpoint = endpoint
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._stop = stop

    @property
    def endpoint(self) -> OpenAICompatibleEndpoint:
        return self._endpoint

    def generate(self, messages: list[dict]) -> str:
        payload = self._build_payload(messages, stream=False)
        try:
            resp = httpx.post(
                f"{self._endpoint.base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0].get("message", {})
            return (message.get("content") or "").strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"{self._request_label()} request failed: {exc}") from exc

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, str]]:
        payload = self._build_payload(messages, stream=True)
        try:
            with httpx.stream(
                "POST",
                f"{self._endpoint.base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        think = self._extract_think_delta(delta)
                        text = self._extract_content_delta(delta)
                        if think:
                            yield ("think", think)
                        if text:
                            yield ("content", text)
                    except json.JSONDecodeError:
                        printable = data_str[:120]
                        print(
                            f"[sustech-rag] skipped malformed {self._malformed_sse_label()}: {printable}",
                            flush=True,
                        )
                        continue
        except httpx.HTTPError as exc:
            raise RuntimeError(f"{self._request_label()} stream request failed: {exc}") from exc

    def _build_payload(self, messages: list[dict], stream: bool) -> dict[str, object]:
        payload: dict[str, object] = {
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": stream,
        }
        if self._stop:
            payload["stop"] = self._stop
        payload.update(self._extra_payload())
        return payload

    def _auth_headers(self) -> dict[str, str]:
        if not self._endpoint.api_key:
            return {}
        return {"Authorization": f"Bearer {self._endpoint.api_key}"}

    def _extra_payload(self) -> dict[str, object]:
        return {}

    def _extract_content_delta(self, delta: dict[str, object]) -> str:
        value = delta.get("content")
        return value if isinstance(value, str) else ""

    def _extract_think_delta(self, delta: dict[str, object]) -> str:
        value = delta.get("reasoning_content")
        return value if isinstance(value, str) else ""

    @abstractmethod
    def _request_label(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _malformed_sse_label(self) -> str:
        raise NotImplementedError


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
