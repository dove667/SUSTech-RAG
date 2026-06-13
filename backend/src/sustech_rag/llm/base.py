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
        top_p: float = 0.95,
        top_k: int = 0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        structured_output_mode: str = "json_schema",
    ) -> None:
        self._endpoint = endpoint
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._stop = stop
        self._top_p = top_p
        self._top_k = top_k if top_k > 0 else 0
        self._frequency_penalty = frequency_penalty
        self._presence_penalty = presence_penalty
        self._structured_output_mode = structured_output_mode

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
        if self._top_p != 1.0:
            payload["top_p"] = self._top_p
        if self._top_k > 0:
            payload["top_k"] = self._top_k
        if self._frequency_penalty != 0.0:
            payload["frequency_penalty"] = self._frequency_penalty
        if self._presence_penalty != 0.0:
            payload["presence_penalty"] = self._presence_penalty
        payload.update(self._extra_payload())
        return payload

    def _auth_headers(self) -> dict[str, str]:
        if not self._endpoint.api_key:
            return {}
        return {"Authorization": f"Bearer {self._endpoint.api_key}"}

    def _extra_payload(self) -> dict[str, object]:
        return {}

    # ------------------------------------------------------------------
    # structured / constrained generation
    # ------------------------------------------------------------------

    def generate_with_schema(self, messages: list[dict], json_schema: dict) -> dict[str, object]:
        """生成受 JSON schema 约束的输出，返回解析后的 dict；失败返回 {}。"""
        payload = self._build_payload(messages, stream=False)
        self._apply_structured_output(payload, json_schema)
        try:
            resp = httpx.post(
                f"{self._endpoint.base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0].get("message", {}).get("content") or ""
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                return parsed
            return {}
        except Exception:
            return {}

    def _apply_structured_output(self, payload: dict[str, object], json_schema: dict) -> None:
        """子类覆写以注入后端特定的 structured output 参数。"""

    @staticmethod
    def _schema_to_gbnf(schema: dict) -> str:
        """将简单 JSON schema 转换为 GBNF grammar 字符串。"""

        def _json_type(prop: dict) -> str:
            t = prop.get("type", "string")
            if t == "boolean":
                return "boolean"
            if t == "integer":
                return "integer"
            if t == "number":
                return "number"
            if t == "array":
                items = prop.get("items", {})
                return f"array-of-{_json_type(items)}"
            return "string"

        rules: list[str] = []
        properties = schema.get("properties", {})
        prop_names = list(properties.keys())

        # basic primitives
        rules.append("ws ::= [ \\t\\n]*")
        rules.append('boolean ::= "true" | "false"')
        rules.append('integer ::= "-"? [0-9]+')
        rules.append('number ::= "-"? [0-9]+ ( "." [0-9]+ )?')
        rules.append(
            'string ::= "\\"" ( [^"\\\\] | "\\\\" ( ["\\\\/bfnrt] '
            '| "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] ) )* "\\""'
        )

        # build object rule
        parts: list[str] = ['"{"']
        for i, name in enumerate(prop_names):
            if i == 0:
                parts.append("ws")
            else:
                parts.append('ws "," ws')
            escaped = json.dumps(name)
            parts.append(escaped)
            parts.append("ws")
            parts.append('":"')
            parts.append("ws")
            ptype = _json_type(properties[name])
            parts.append(ptype)
            parts.append("ws")
        parts.append('"}"')
        rules.append(f"root ::= {' '.join(parts)}")

        # handle array-of-X rules for nested items
        for name in prop_names:
            prop = properties[name]
            if prop.get("type") == "array":
                items = prop.get("items", {})
                item_type = _json_type(items)
                if item_type.startswith("array-of-"):
                    inner = item_type[len("array-of-"):]
                    # array of objects
                    if items.get("type") == "object":
                        sub_props = items.get("properties", {})
                        sub_names = list(sub_props.keys())
                        sub_parts: list[str] = ['"{"']
                        for j, sn in enumerate(sub_names):
                            if j == 0:
                                sub_parts.append("ws")
                            else:
                                sub_parts.append('ws "," ws')
                            escaped_sn = json.dumps(sn)
                            sub_parts.append(escaped_sn)
                            sub_parts.append("ws")
                            sub_parts.append('":"')
                            sub_parts.append("ws")
                            sub_parts.append(_json_type(sub_props[sn]))
                            sub_parts.append("ws")
                        sub_parts.append('"}"')
                        rules.append(
                            f"array-element ::= {' '.join(sub_parts)}"
                        )
                        rules.append(
                            'array-of-object ::='
                            ' "[" ws ( array-element ( ws "," ws array-element )* )? ws "]"'
                        )
                    else:
                        rules.append(
                            f'array-of-{inner} ::='
                            f' "[" ws ( {inner} ( ws "," ws {inner} )* )? ws "]"'
                        )
                else:
                    rules.append(
                        f'array-of-{item_type} ::='
                        f' "[" ws ( {item_type} ( ws "," ws {item_type} )* )? ws "]"'
                    )

        return "\n".join(rules)

    # ------------------------------------------------------------------
    # auth / helpers
    # ------------------------------------------------------------------

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
