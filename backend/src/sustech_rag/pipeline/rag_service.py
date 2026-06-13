from __future__ import annotations

import threading
from collections.abc import Generator, Iterator
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
from sustech_rag.pipeline.single_pass import (
    SinglePassController,
    RetrievalResult,
    RouterResult,
)
from sustech_rag.retrieval.engine import RetrievalEngine
from sustech_rag.retrieval.reranker import RetrievedChunk

_SIMPLE_RAG_SYSTEM_PROMPT = (
    "你是南方科技大学的校园知识库问答助手。"
    "请优先依据提供的检索上下文回答用户问题。"
    "如果检索上下文不足以支持答案，请明确说明当前知识库信息不足，不要编造事实。"
    "若用户请求明显与南方科技大学校园知识库服务无关，请简短礼貌拒绝，并引导用户提问南方科技大学相关问题。"
    "回答请使用中文，尽量简洁、准确；若使用了检索材料，尽量引用信息来源标题。"
)

_SELF_RAG_RETRIEVAL_SYSTEM_PROMPT = (
    "你是南方科技大学的校园知识库问答助手。"
    "当前问题已经过路由判断，需要依据提供的检索上下文回答。"
    "请严格只根据检索上下文与对话历史作答。"
    "如果检索上下文中没有明确给出某个具体事实（如数字、名称、日期、流程步骤），"
    "你必须告知用户该信息在当前知识库中未找到，禁止根据常识或推断补充任何具体信息。"
    "回答请使用中文，尽量简洁、准确，并尽量引用信息来源标题。"
)

_SELF_RAG_OUT_OF_SCOPE_SYSTEM_PROMPT = (
    "你是南方科技大学的校园知识库问答助手。"
    "当前请求已经被判定为超出服务范围。"
    "请用 1 到 2 句中文礼貌拒绝，不要回答原问题本身。"
    "同时引导用户提出与南方科技大学校园信息、机构、课程、招生、科研、办事流程或公开通知相关的问题。"
)

_SELF_RAG_INSUFFICIENT_EVIDENCE_SYSTEM_PROMPT = (
    "你是南方科技大学的校园知识库问答助手。"
    "经过多轮检索，知识库中没有找到能够可靠支撑回答该问题的证据。"
    "你必须如实告知用户：当前知识库中没有足够的资料来回答这个问题。"
    "禁止根据常识、推断或外部知识作答，禁止给出任何具体数字、事实或结论。"
    "回答请使用中文，1 到 2 句话，简洁说明证据不足，并建议用户通过官方渠道（如南科大官网）查询。"
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
        self._single_pass = SinglePassController(self.llm, config.retrieval.max_rounds)

    def _build_chat_messages(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[dict],
        system_prompt: str,
    ) -> list[dict]:
        """Build ChatML messages with system prompt + context + conversation history."""
        context = "\n\n".join(
            f"[{idx + 1}] {chunk.metadata.get('title', 'Untitled')}\n{chunk.text}"
            for idx, chunk in enumerate(chunks)
        )
        system_content = system_prompt
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
            messages = self._build_chat_messages(query, plan.chunks, [], plan.system_prompt)
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

            # 根据模式选择流水线
            if self.config.retrieval.mode == "single_pass":
                yield from self._answer_stream_single_pass(query, history, cancel_event)
                return

            plan = yield from self._plan_answer_stream(
                query,
                history,
                cancel_event=cancel_event,
                emit_debug_events=True,
            )

            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")

            chat_messages = self._build_chat_messages(
                query,
                plan.chunks,
                history,
                plan.system_prompt,
            )

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
        return self._consume_answer_plan_stream(
            self._plan_answer_stream(query, history, emit_debug_events=False)
        )

    def _consume_answer_plan_stream(
        self,
        stream: Generator[tuple[str, object], None, AnswerPlan],
    ) -> AnswerPlan:
        while True:
            try:
                next(stream)
            except StopIteration as stop:
                return stop.value

    def _plan_answer_stream(
        self,
        query: str,
        history: list[dict],
        *,
        cancel_event: threading.Event | None = None,
        emit_debug_events: bool,
    ) -> Generator[tuple[str, object], None, AnswerPlan]:
        if self.config.retrieval.mode != "self_rag":
            plan = AnswerPlan(
                chunks=self.retrieval.retrieve(query),
                requires_retrieval=True,
                system_prompt=_SIMPLE_RAG_SYSTEM_PROMPT,
            )
            if emit_debug_events and plan.chunks:
                yield ("reference", plan.chunks)
            return plan

        debug_events: list[SelfRAGDebugEvent] = []
        decision = self._self_rag.should_retrieve(query, history)
        decision_event = self._build_retrieval_decision_event(decision)
        debug_events.append(decision_event)
        if emit_debug_events:
            yield (decision_event.event, decision_event.payload)
        if not decision.should_retrieve:
            return AnswerPlan(
                chunks=[],
                requires_retrieval=False,
                system_prompt=_SELF_RAG_OUT_OF_SCOPE_SYSTEM_PROMPT,
                debug_events=debug_events,
            )

        accumulated: list[RetrievedChunk] = []
        accepted_texts: set[str] = set()
        seen_texts: set[str] = set()

        for round_index in range(1, self._self_rag.max_rounds + 1):
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")
            candidates = self.retrieval.retrieve(query, exclude_texts=seen_texts)
            if not candidates:
                break

            seen_texts.update(chunk.text for chunk in candidates)
            assessments = self._self_rag.assess_chunk_relevance(query, candidates)
            assessment_event = self._build_retrieval_assessment_event(
                round_index, candidates, assessments
            )
            debug_events.append(assessment_event)
            if emit_debug_events:
                yield (assessment_event.event, assessment_event.payload)
            relevant = self._self_rag.filter_relevant_chunks(
                query,
                candidates,
                decisions=assessments,
            )
            if not relevant:
                continue

            newly_accepted: list[RetrievedChunk] = []
            for chunk in relevant:
                if chunk.text in accepted_texts:
                    continue
                accepted_texts.add(chunk.text)
                accumulated.append(chunk)
                newly_accepted.append(chunk)

            if emit_debug_events and newly_accepted:
                yield ("reference", newly_accepted)

            draft_messages = self._build_chat_messages(
                query,
                accumulated,
                history,
                _SELF_RAG_RETRIEVAL_SYSTEM_PROMPT,
            )
            draft_answer = self.llm.generate(draft_messages)
            support = self._self_rag.is_answer_supported(query, draft_answer, accumulated)
            support_event = self._build_support_decision_event(round_index, support)
            debug_events.append(support_event)
            if emit_debug_events:
                yield (support_event.event, support_event.payload)
            if support.supported:
                return AnswerPlan(
                    chunks=accumulated,
                    requires_retrieval=True,
                    system_prompt=_SELF_RAG_RETRIEVAL_SYSTEM_PROMPT,
                    debug_events=debug_events,
                )

        last_support_failed = (
            debug_events
            and debug_events[-1].event == "support.decision"
            and not debug_events[-1].payload.get("supported", True)
        )
        fallback_prompt = (
            _SELF_RAG_INSUFFICIENT_EVIDENCE_SYSTEM_PROMPT
            if (not accumulated or last_support_failed)
            else _SELF_RAG_RETRIEVAL_SYSTEM_PROMPT
        )
        return AnswerPlan(
            chunks=accumulated,
            requires_retrieval=True,
            system_prompt=fallback_prompt,
            debug_events=debug_events,
        )

    def _build_retrieval_decision_event(
        self,
        decision: RetrievalDecision,
    ) -> SelfRAGDebugEvent:
        thought = (
            decision.reason.strip()
            or (
                "这个问题需要先查资料。"
                if decision.should_retrieve
                else "这个问题不在南科大知识库问答范围内。"
            )
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
                    "url": str(chunk.metadata.get("source_url") or ""),
                    "source": str(chunk.metadata.get("source") or ""),
                    "score": float(chunk.score),
                    "relevant": relevant,
                    "snippet": chunk.text[:400] if len(chunk.text) > 400 else chunk.text,
                    "full_text": chunk.text,
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
            or (
                "现有证据已经足够支撑回答。"
                if decision.supported
                else "现有证据还不够，需要继续查。"
            )
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

    # ------------------------------------------------------------------
    # Single-Pass RAG: 单次生成完成路由→检索分析→草稿→自检→输出
    # ------------------------------------------------------------------

    def _answer_stream_single_pass(
        self,
        query: str,
        history: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, object]]:
        """单次生成流水线：路由→检索→分析→输出。"""

        # ---- Step 1: 路由判断（含 XML 格式重试）----
        router_msgs = self._single_pass.build_router_messages(query, history)
        router_text = self._single_pass._generate_with_xml_retry(
            router_msgs,
            required_tags=["retrieval_decision", "should_retrieve"],
            required_any_tag=None,
        )
        if cancel_event is not None and cancel_event.is_set():
            raise GenerationCancelledError("generation cancelled")
        router = self._single_pass.parse_router_output(router_text)

        # 发送路由决策事件
        yield (
            "retrieval.decision",
            {
                "mode": "single_pass",
                "should_retrieve": router.should_retrieve,
                "thought": router.reason or (
                    "需要检索资料。" if router.should_retrieve
                    else "无需检索，直接回答。"
                ),
            },
        )

        # 无需检索 → 直接流式输出回答
        if not router.should_retrieve:
            if router.output:
                yield ("content.delta", router.output)
            else:
                yield (
                    "content.delta",
                    "您的问题不在南科大知识库范围内，请提问与南方科技大学相关的问题。",
                )
            yield ("done", {"finish_reason": "stop", "usage": {}})
            return

        # ---- Step 2-4: 检索 + 分析 + 自检 + 输出 ----
        all_chunks: list[RetrievedChunk] = []
        seen_texts: set[str] = set()
        final_output = ""

        for round_idx in range(1, self._single_pass.max_rounds + 1):
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")

            # 发送检索中状态
            yield (
                "retrieval.assessment",
                {
                    "round": round_idx,
                    "thought": f"第 {round_idx} 轮检索中，正在搜索相关文档...",
                    "items": [],
                },
            )

            # 检索
            candidates = self.retrieval.retrieve(query, exclude_texts=seen_texts)
            if not candidates:
                yield (
                    "support.decision",
                    {
                        "round": round_idx,
                        "supported": False,
                        "thought": "没有找到更多相关文档。",
                    },
                )
                break

            seen_texts.update(chunk.text for chunk in candidates)

            # 发送引用
            yield ("reference", candidates)

            # 构建 prompt 并生成（含 XML 格式重试）
            retrieval_msgs = self._single_pass.build_retrieval_messages(
                query, candidates, history
            )
            retrieval_text = self._single_pass._generate_with_xml_retry(
                retrieval_msgs,
                required_tags=["relevance_analysis", "draft", "self_check"],
                required_any_tag=["output", "need_more_retrieval"],
            )
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelledError("generation cancelled")

            result = self._single_pass.parse_retrieval_output(retrieval_text)

            # 发送分析进度
            if result.relevance_analysis:
                yield (
                    "retrieval.assessment",
                    {
                        "round": round_idx,
                        "thought": result.relevance_analysis[:300],
                        "items": [],
                    },
                )
            if result.draft:
                yield (
                    "retrieval.assessment",
                    {
                        "round": round_idx,
                        "thought": f"草稿：\n{result.draft[:300]}",
                        "items": [],
                    },
                )
            if result.self_check:
                yield (
                    "support.decision",
                    {
                        "round": round_idx,
                        "supported": result.is_supported,
                        "thought": result.self_check[:300],
                    },
                )

            # 累积相关文档
            for chunk in candidates:
                if chunk.text not in {c.text for c in all_chunks}:
                    all_chunks.append(chunk)

            # 判断是否完成
            if result.output:
                final_output = result.output
                break

            if not result.need_more:
                # 没输出也没请求更多 → 最后一轮无结果
                break

        # 流式输出最终回答
        if final_output:
            yield ("content.delta", final_output)
        elif all_chunks:
            # 有检索结果但没有 output → 用传统方式流式生成
            chat_msgs = self._build_chat_messages(
                query,
                all_chunks,
                history,
                _SELF_RAG_RETRIEVAL_SYSTEM_PROMPT,
            )
            think_open = False
            for event_type, text in self.llm.generate_stream(
                chat_msgs,
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
            if think_open:
                yield ("think.end", None)
        else:
            yield (
                "content.delta",
                "抱歉，当前知识库中没有足够的信息来回答这个问题。"
                "建议通过南科大官网查询更多信息。",
            )

        yield ("done", {"finish_reason": "stop", "usage": {}})
