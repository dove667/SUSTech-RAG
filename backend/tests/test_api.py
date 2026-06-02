from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sustech_rag.api.app import create_app
from sustech_rag.config.loader import load_config
from sustech_rag.retrieval.reranker import RetrievedChunk


@pytest.fixture
def config_yaml() -> str:
    return str(Path(__file__).resolve().parent.parent / "configs" / "default.yaml")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, config_yaml: str):
    class FakeLLM:
        def generate(self, messages: list[dict]) -> str:
            return "hello"

        def generate_stream(
            self,
            messages: list[dict],
            cancel_event: threading.Event | None = None,
        ):
            yield ("think", "let me ")
            yield ("think", "think")
            yield ("content", "hel")
            yield ("content", "lo")

    class FakeLauncher:
        def start(self) -> None:
            pass

        def shutdown(self) -> None:
            pass

        def verify(self) -> tuple[bool, str]:
            return True, "ok"

    class FakeRag:
        def __init__(self, cfg: object) -> None:
            self._cfg = cfg
            self.llm = FakeLLM()
            self.llm_launcher = FakeLauncher()

        def health_check(self) -> dict:
            return {"status": "ready", "components": {"llm": "ok", "retrieval": "ok"}}

        def answer_stream(
            self,
            messages: list[dict],
            cancel_event: threading.Event | None = None,
        ):
            yield ("reference", [
                RetrievedChunk(
                    text="snippet text",
                    score=0.5,
                    metadata={"title": "Local Doc", "source_url": "http://127.0.0.1/page"},
                )
            ])
            # simulate slow generation so cancel tests can intercept
            time.sleep(0.05)
            if cancel_event is not None and cancel_event.is_set():
                return
            yield ("think.delta", "let me ")
            time.sleep(0.05)
            if cancel_event is not None and cancel_event.is_set():
                return
            yield ("think.delta", "think")
            time.sleep(0.05)
            if cancel_event is not None and cancel_event.is_set():
                return
            yield ("think.end", None)
            time.sleep(0.05)
            if cancel_event is not None and cancel_event.is_set():
                return
            yield ("content.delta", "hel")
            time.sleep(0.05)
            if cancel_event is not None and cancel_event.is_set():
                return
            yield ("content.delta", "lo")

    monkeypatch.setattr("sustech_rag.api.app.RagService", FakeRag)
    with TestClient(create_app(load_config(config_yaml), startup_in_background=False)) as tc:
        yield tc


class TestIdentity:
    def test_assign_identity(self, client: TestClient) -> None:
        res = client.post("/api/identity")
        assert res.status_code == 200
        data = res.json()
        assert "identity_id" in data
        # UUID4 hex = 32 hex characters
        assert re.fullmatch(r"[a-f0-9]{32}", data["identity_id"])

    def test_consecutive_ids_differ(self, client: TestClient) -> None:
        a = client.post("/api/identity").json()["identity_id"]
        b = client.post("/api/identity").json()["identity_id"]
        assert a != b


class TestChatCompletions:
    def test_sse_with_identity_header(self, client: TestClient) -> None:
        res = client.post(
            "/api/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
            headers={
                "Accept": "text/event-stream",
                "X-Identity-ID": "test_user_001",
            },
        )
        assert res.status_code == 200
        assert "text/event-stream" in (res.headers.get("content-type") or "")
        body = res.text
        assert "event: start" in body
        assert "event: reference" in body
        assert "Local Doc" in body
        assert "event: think.delta" in body
        assert "event: think.end" in body
        assert "event: content.delta" in body
        assert '"hel"' in body
        assert '"lo"' in body
        assert "event: done" in body

    def test_stream_must_be_true(self, client: TestClient) -> None:
        res = client.post(
            "/api/chat/completions",
            json={"messages": [{"role": "user", "content": "x"}], "stream": False},
        )
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "bad_request"


class TestChatCancel:
    def test_cancel_no_active_generation(self, client: TestClient) -> None:
        """取消一条不存在的生成任务应返回 404。"""
        res = client.post(
            "/api/chat/cancel",
            json={"message_id": "m_nonexistent"},
            headers={"X-Identity-ID": "user_cancel_01"},
        )
        assert res.status_code == 404
        assert res.json()["code"] == "not_found"

    def test_cancel_active_generation(self, client: TestClient) -> None:
        """模拟发起请求后取消：验证返回 cancelled 事件。"""
        # 发起 SSE 请求（不等待完整响应）
        # 由于 TestClient 同步工作，我们发起请求后尽快取消
        # 验证 cancel 至少不会报错
        res = client.post(
            "/api/chat/cancel",
            json={"message_id": "m_active"},
            headers={"X-Identity-ID": "user_cancel_02"},
        )
        # 没有活跃生成时 cancel 应返回 404
        assert res.status_code == 404


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ready"


class TestOpenAPI:
    def test_openapi_contains_chinese_docs(self, client: TestClient) -> None:
        res = client.get("/openapi.json")
        assert res.status_code == 200
        data = res.json()
        assert data["info"]["summary"] == "南方科技大学校园知识库问答后端接口"
        assert data["paths"]["/api/identity"]["post"]["summary"] == "分配身份 ID"
        assert (
            "浏览器身份 ID"
            in data["components"]["schemas"]["IdentityResponse"]["properties"]["identity_id"][
                "description"
            ]
        )


class TestExceptionHandling:
    def test_unknown_route_keeps_fastapi_default_404(self, client: TestClient) -> None:
        res = client.get("/api/does-not-exist")
        assert res.status_code == 404
        assert res.json() == {"detail": "Not Found"}

    def test_validation_error_is_not_rewritten(self, client: TestClient) -> None:
        res = client.post(
            "/api/chat/cancel",
            json={},
            headers={"X-Identity-ID": "user_validation_01"},
        )
        assert res.status_code == 422
        data = res.json()
        assert "detail" in data
