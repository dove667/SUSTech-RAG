from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from sustech_rag.config.models import AppConfig
from sustech_rag.llm import create_llm_runtime
from sustech_rag.pipeline.schemas import (
    AnswerPlan,
    ChunkRelevanceDecision,
    RetrievalDecision,
    SelfRAGDebugEvent,
    SupportDecision,
)
from sustech_rag.pipeline.self_rag import SelfRAGController
from sustech_rag.retrieval.engine import RetrievalEngine
from sustech_rag.retrieval.reranker import RetrievedChunk

_DEFAULT_SYSTEM_PROMPT = (
    "你是南方科技大学的校园知识库问答助手。请基于提供的检索上下文回答问题，"
    "如果上下文不足，请明确说明, 不要编造信息。"
    "请给出简洁、准确的中文回答，并尽量引用信息来源标题。"
    "如果用户询问与南方科技大学无关的问题，请礼貌拒绝回答。"
)

class GenerationCancelledError(RuntimeError):
    """当前请求在进入或执行生成流程时被取消。"""


class RagService:
    """封装 simple RAG 与 self-RAG 的检索编排与生成服务。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.retrieval = RetrievalEngine(config)
        runtime = create_llm_runtime(config)
        self.llm = runtime.client
        self.llm_launcher = runtime.launcher
        self._request_slots = max(1, config.llm.max_concurrent_requests)
        self._request_semaphore = threading.BoundedSemaphore(self._request_slots)
        self._self_rag = SelfRAGController(self.llm, config.retrieval.max_rounds)

    def _build_chat_messages(
        self, query: str, chunks: list[RetrievedChunk], history: list[dict]
    ) -> list[dict]:
        """Build ChatML messages with system prompt + context + conversation history."""
        context = "\n\n".join(
            f"[{idx + 1}] {chunk.metadata.get('title', 'Untitled')}\n{chunk.text}"
            for idx, chunk in enumerate(chunks)
        )
        system_content = _DEFAULT_SYSTEM_PROMPT
        if chunks:
            system_content += f"\n\n检索上下文：\n{context}"

        messages: list[dict] = [{"role": "system", "content": system_content}]
        for m in history:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant") and content.strip():
                messages.append({"role": role, "content": content.strip()})
        if (
            not messages
            or messages[-1].get("role") != "user"
            or messages[-1].get("content") != query
        ):
            messages.append({"role": "user", "content": query})
        return messages

    def _extract_last_user_query(self, messages: list[dict]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user" and (m.get("content") or "").strip():
                return m["content"].strip()
        raise ValueError("no user message found in conversation")

    def answer(self, query: str) -> str:
        with self._acquire_request_slot():
            plan = self._plan_answer(query, [])
            messages = self._build_chat_messages(query, plan.chunks, [])
            return self.llm.generate(messages)

    def answer_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, object]]:
        with self._acquire_request_slot(cancel_event):
            query = self._extract_last_user_query(messages)
            history = [m for m in messages if m.get("content", "").strip()]
            if history and history[-1].get("content", "").strip() == query:
                history = history[:-1]

            plan = self._plan_answer(query, history)

            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")

            for debug_event in plan.debug_events:
                yield (debug_event.event, debug_event.payload)

            if plan.requires_retrieval and plan.chunks:
                yield ("reference", plan.chunks)

            chat_messages = self._build_chat_messages(query, plan.chunks, history)

            think_open = False
            for event_type, text in self.llm.generate_stream(
                chat_messages,
                cancel_event=cancel_event,
            ):
                if cancel_event is not None and cancel_event.is_set():
                    raise GenerationCancelledError("generation cancelled")
                if event_type == "think":
                    if not think_open:
                        think_open = True
                    yield ("think.delta", text)
                elif event_type == "content":
                    if think_open:
                        yield ("think.end", None)
                        think_open = False
                    yield ("content.delta", text)

            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")

            if think_open:
                yield ("think.end", None)

    def health_check(self) -> dict:
        components = {}
        try:
            _ = self.retrieval.index
            components["retrieval"] = "ok"
        except Exception as exc:
            components["retrieval"] = str(exc)

        llm_ok, llm_msg = self.llm_launcher.verify()
        components["llm"] = llm_msg

        all_ok = all(v == "ok" for v in components.values())
        return {
            "status": "ready" if all_ok else "error",
            "components": components,
        }

    def _plan_answer(self, query: str, history: list[dict]) -> AnswerPlan:
        if self.config.retrieval.mode != "self_rag":
            return AnswerPlan(
                chunks=self.retrieval.retrieve(query),
                requires_retrieval=True,
            )

        debug_events: list[SelfRAGDebugEvent] = []
        decision = self._self_rag.should_retrieve(query, history)
        debug_events.append(self._build_retrieval_decision_event(decision))
        if not decision.should_retrieve:
            return AnswerPlan(
                chunks=[],
                requires_retrieval=False,
                debug_events=debug_events,
            )

        accumulated: list[RetrievedChunk] = []
        accepted_texts: set[str] = set()
        seen_texts: set[str] = set()

        for round_index in range(1, self._self_rag.max_rounds + 1):
            candidates = self.retrieval.retrieve(query, exclude_texts=seen_texts)
            if not candidates:
                break

            seen_texts.update(chunk.text for chunk in candidates)
            assessments = self._self_rag.assess_chunk_relevance(query, candidates)
            debug_events.append(
                self._build_retrieval_assessment_event(round_index, candidates, assessments)
            )
            relevant = self._self_rag.filter_relevant_chunks(
                query,
                candidates,
                decisions=assessments,
            )
            if not relevant:
                continue

            for chunk in relevant:
                if chunk.text in accepted_texts:
                    continue
                accepted_texts.add(chunk.text)
                accumulated.append(chunk)

            draft_messages = self._build_chat_messages(query, accumulated, history)
            draft_answer = self.llm.generate(draft_messages)
            support = self._self_rag.is_answer_supported(query, draft_answer, accumulated)
            debug_events.append(self._build_support_decision_event(round_index, support))
            if support.supported:
                return AnswerPlan(
                    chunks=accumulated,
                    requires_retrieval=True,
                    debug_events=debug_events,
                )

        return AnswerPlan(
            chunks=accumulated,
            requires_retrieval=True,
            debug_events=debug_events,
        )

    def _build_retrieval_decision_event(
        self,
        decision: RetrievalDecision,
    ) -> SelfRAGDebugEvent:
        thought = (
            decision.reason.strip()
            or ("这个问题需要先查资料。" if decision.should_retrieve else "这个问题可以直接回答。")
        )
        return SelfRAGDebugEvent(
            event="retrieval.decision",
            payload={
                "mode": "self_rag",
                "should_retrieve": decision.should_retrieve,
                "thought": thought,
            },
        )

    def _build_retrieval_assessment_event(
        self,
        round_index: int,
        candidates: list[RetrievedChunk],
        assessments: list[ChunkRelevanceDecision],
    ) -> SelfRAGDebugEvent:
        by_index = {item.candidate_index: item for item in assessments}
        items: list[dict[str, object]] = []
        relevant_count = 0
        for idx, chunk in enumerate(candidates, 1):
            assessment = by_index.get(idx)
            relevant = bool(assessment.relevant) if assessment is not None else False
            if relevant:
                relevant_count += 1
            items.append(
                {
                    "candidate_index": idx,
                    "title": str(chunk.metadata.get("title") or "Untitled"),
                    "source": str(chunk.metadata.get("source") or ""),
                    "relevant": relevant,
                    "thought": (
                        assessment.reason.strip()
                        if assessment is not None and assessment.reason.strip()
                        else ("这条资料相关。" if relevant else "这条资料帮助不大。")
                    ),
                }
            )
        return SelfRAGDebugEvent(
            event="retrieval.assessment",
            payload={
                "round": round_index,
                "thought": f"第 {round_index} 轮筛出了 {relevant_count} 条相关资料。",
                "items": items,
            },
        )

    def _build_support_decision_event(
        self,
        round_index: int,
        decision: SupportDecision,
    ) -> SelfRAGDebugEvent:
        thought = (
            decision.reason.strip()
            or ("现有证据已经足够支撑回答。" if decision.supported else "现有证据还不够，需要继续查。")
        )
        return SelfRAGDebugEvent(
            event="support.decision",
            payload={
                "round": round_index,
                "supported": decision.supported,
                "thought": thought,
            },
        )

    @contextmanager
    def _acquire_request_slot(
        self,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[None]:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")
            if self._request_semaphore.acquire(timeout=0.05):
                break
        try:
            yield
        finally:
            self._request_semaphore.release()
