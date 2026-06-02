from __future__ import annotations

import threading
from types import SimpleNamespace

from sustech_rag.pipeline.rag_service import RagService
from sustech_rag.pipeline.self_rag import SelfRAGController
from sustech_rag.pipeline.schemas import ChunkRelevanceDecision
from sustech_rag.retrieval.reranker import RetrievedChunk


class FakeJudgeLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def generate(self, messages: list[dict]) -> str:
        return self._responses.pop(0)

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ):
        yield ("content", "unused")


def test_self_rag_controller_parses_json_decisions() -> None:
    llm = FakeJudgeLLM(
        [
            '{"should_retrieve": true, "reason": "需要校园事实"}',
            '{"assessments": [{"candidate_index": 1, "relevant": false, "reason": "不相关"}, {"candidate_index": 2, "relevant": true, "reason": "第二篇最相关"}]}',
            '{"assessments": [{"candidate_index": 1, "relevant": false, "reason": "不相关"}, {"candidate_index": 2, "relevant": true, "reason": "第二篇最相关"}]}',
            '{"supported": true, "reason": "证据充分"}',
        ]
    )
    controller = SelfRAGController(llm, max_rounds=2)
    chunks = [
        RetrievedChunk(text="A", score=0.1, metadata={"title": "Doc A"}),
        RetrievedChunk(text="B", score=0.2, metadata={"title": "Doc B"}),
    ]

    decision = controller.should_retrieve("南科大有哪些学院？", [])
    decisions = controller.assess_chunk_relevance("南科大有哪些学院？", chunks)
    relevant = controller.filter_relevant_chunks("南科大有哪些学院？", chunks)
    support = controller.is_answer_supported("南科大有哪些学院？", "有很多学院", relevant)

    assert decision.should_retrieve is True
    assert decisions == [
        ChunkRelevanceDecision(candidate_index=1, relevant=False, reason="不相关"),
        ChunkRelevanceDecision(candidate_index=2, relevant=True, reason="第二篇最相关"),
    ]
    assert [chunk.text for chunk in relevant] == ["B"]
    assert support.supported is True


class FakeRetrieval:
    def __init__(self, responses: list[list[RetrievedChunk]]) -> None:
        self.responses = list(responses)
        self.calls: list[set[str]] = []

    def retrieve(
        self,
        query: str,
        *,
        exclude_texts: set[str] | None = None,
        top_n: int | None = None,
    ):
        self.calls.append(set(exclude_texts or set()))
        if not self.responses:
            return []
        return self.responses.pop(0)


class FakeAnswerLLM:
    def __init__(self) -> None:
        self.generate_calls: list[list[dict]] = []

    def generate(self, messages: list[dict]) -> str:
        self.generate_calls.append(messages)
        return "draft answer"

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ):
        yield ("content", "final")


class FakeSelfRAG:
    def __init__(
        self,
        should_retrieve: bool,
        relevant_rounds: list[list[RetrievedChunk]],
        supported: list[bool],
    ) -> None:
        self.max_rounds = max(1, len(relevant_rounds))
        self._should_retrieve = should_retrieve
        self._relevant_rounds = list(relevant_rounds)
        self._supported = list(supported)

    def should_retrieve(self, query: str, history: list[dict]):
        return SimpleNamespace(should_retrieve=self._should_retrieve, reason="")

    def filter_relevant_chunks(
        self,
        query: str,
        candidates: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        return self._relevant_rounds.pop(0)

    def is_answer_supported(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
    ):
        return SimpleNamespace(supported=self._supported.pop(0), reason="")


def _make_service(
    fake_retrieval: FakeRetrieval,
    fake_llm: FakeAnswerLLM,
    fake_self_rag: FakeSelfRAG,
) -> RagService:
    service = object.__new__(RagService)
    service.config = SimpleNamespace(retrieval=SimpleNamespace(mode="self_rag"))
    service.retrieval = fake_retrieval
    service.llm = fake_llm
    service.llm_launcher = SimpleNamespace(verify=lambda: (True, "ok"))
    service._request_slots = 1
    service._request_semaphore = threading.BoundedSemaphore(1)
    service._self_rag = fake_self_rag
    return service


def test_self_rag_can_skip_retrieval() -> None:
    service = _make_service(
        FakeRetrieval([]),
        FakeAnswerLLM(),
        FakeSelfRAG(should_retrieve=False, relevant_rounds=[], supported=[]),
    )

    plan = service._plan_answer("你好", [])

    assert plan.requires_retrieval is False
    assert plan.chunks == []
    assert service.retrieval.calls == []


def test_self_rag_retries_with_seen_chunk_exclusion() -> None:
    first = RetrievedChunk(text="Doc-1", score=0.9, metadata={"title": "Doc 1"})
    second = RetrievedChunk(text="Doc-2", score=0.8, metadata={"title": "Doc 2"})
    retrieval = FakeRetrieval([[first], [second]])
    llm = FakeAnswerLLM()
    service = _make_service(
        retrieval,
        llm,
        FakeSelfRAG(
            should_retrieve=True,
            relevant_rounds=[[first], [second]],
            supported=[False, True],
        ),
    )

    plan = service._plan_answer("南科大有哪些学院？", [])

    assert plan.requires_retrieval is True
    assert [chunk.text for chunk in plan.chunks] == ["Doc-1", "Doc-2"]
    assert retrieval.calls == [set(), {"Doc-1"}]
    assert len(llm.generate_calls) == 2
