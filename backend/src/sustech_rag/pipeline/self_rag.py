from __future__ import annotations

import json
import re

from sustech_rag.llm.base import LLMClient
from sustech_rag.pipeline.schemas import (
    ChunkRelevanceDecision,
    RetrievalDecision,
    SupportDecision,
)
from sustech_rag.retrieval.reranker import RetrievedChunk

_ROUTER_SYSTEM_PROMPT = (
    "你是南方科技大学校园知识库问答系统的检索路由器。"
    "知识库里保存的是与南方科技大学有关的公开网页信息。"
    "只有当用户问题需要查询、核实或引用南方科技大学相关事实信息时，才应触发检索。"
    "如果问题只是问候、闲聊、助手自我介绍、表达感谢、简单改写，"
    "或者根本不需要查询南方科技大学相关信息，就不应检索。"
    "只返回 JSON。"
)

_RELEVANCE_SYSTEM_PROMPT = (
    "你是一个检索过滤器。请根据问题判断候选文档是否相关。"
    "相关表示文档能直接帮助回答问题，而不是只提到同名实体。"
    "只返回 JSON。"
)

_SUPPORT_SYSTEM_PROMPT = (
    "你是一个事实支持性审查器。请判断回答是否被提供的文档片段充分支持。"
    "如果回答包含文档里没有明确给出的关键信息，就视为不充分支持。"
    "只返回 JSON。"
)

class SelfRAGController:
    """负责 self-RAG 的检索判定、文档过滤与答案支持性判断。"""

    def __init__(self, llm: LLMClient, max_rounds: int) -> None:
        self._llm = llm
        self.max_rounds = max(1, max_rounds)

    def should_retrieve(self, query: str, history: list[dict]) -> RetrievalDecision:
        history_text = self._format_history(history)
        user_prompt = (
            "请判断下面这个问题，是否需要先检索南方科技大学相关知识库再回答。\n"
            "只有在回答依赖南方科技大学相关事实信息时，才选择 should_retrieve=true。\n"
            f"对话历史：\n{history_text}\n\n"
            f"用户问题：{query}\n\n"
            '输出 JSON，格式为 {"should_retrieve": true, "reason": "..."}。'
        )
        data = self._generate_json(_ROUTER_SYSTEM_PROMPT, user_prompt)
        return RetrievalDecision(
            should_retrieve=bool(data.get("should_retrieve", True)),
            reason=str(data.get("reason", "")),
        )

    def assess_chunk_relevance(
        self,
        query: str,
        candidates: list[RetrievedChunk],
    ) -> list[ChunkRelevanceDecision]:
        if not candidates:
            return []
        docs = []
        for idx, chunk in enumerate(candidates, 1):
            title = str(chunk.metadata.get("title") or "Untitled")
            docs.append(f"[{idx}] {title}\n{chunk.text}")
        joined_docs = "\n\n".join(docs)
        user_prompt = (
            f"用户问题：{query}\n\n"
            "下面是候选文档，请逐条判断是否真正相关。\n\n"
            f"{joined_docs}\n\n"
            '输出 JSON，格式为 {"assessments": [{"candidate_index": 1, "relevant": true, "reason": "..."}]}。'
        )
        data = self._generate_json(_RELEVANCE_SYSTEM_PROMPT, user_prompt)
        decisions: list[ChunkRelevanceDecision] = []
        for raw_item in data.get("assessments", []):
            if not isinstance(raw_item, dict):
                continue
            raw_idx = raw_item.get("candidate_index")
            if not isinstance(raw_idx, int):
                continue
            if 1 <= raw_idx <= len(candidates):
                decisions.append(
                    ChunkRelevanceDecision(
                        candidate_index=raw_idx,
                        relevant=bool(raw_item.get("relevant", False)),
                        reason=str(raw_item.get("reason", "")),
                    )
                )
        return decisions

    def filter_relevant_chunks(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        decisions: list[ChunkRelevanceDecision] | None = None,
    ) -> list[RetrievedChunk]:
        if decisions is None:
            decisions = self.assess_chunk_relevance(query, candidates)
        chosen: list[RetrievedChunk] = []
        for decision in decisions:
            if decision.relevant:
                chosen.append(candidates[decision.candidate_index - 1])
        return chosen

    def is_answer_supported(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> SupportDecision:
        if not chunks:
            return SupportDecision(supported=False, reason="no supporting chunks")
        context = "\n\n".join(
            f"[{idx}] {chunk.metadata.get('title', 'Untitled')}\n{chunk.text}"
            for idx, chunk in enumerate(chunks, 1)
        )
        user_prompt = (
            f"用户问题：{query}\n\n"
            f"候选回答：{answer}\n\n"
            f"证据文档：\n{context}\n\n"
            '输出 JSON，格式为 {"supported": true, "reason": "..."}。'
        )
        data = self._generate_json(_SUPPORT_SYSTEM_PROMPT, user_prompt)
        return SupportDecision(
            supported=bool(data.get("supported", False)),
            reason=str(data.get("reason", "")),
        )

    def _generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, object]:
        text = self._llm.generate(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return self._extract_json_object(text)

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, object]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        candidate = match.group(0) if match else cleaned
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"self-RAG judge returned invalid JSON: {text}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"self-RAG judge returned non-object JSON: {text}")
        return data

    @staticmethod
    def _format_history(history: list[dict]) -> str:
        entries = []
        for item in history[-6:]:
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "").strip()
            if content:
                entries.append(f"{role}: {content}")
        return "\n".join(entries) if entries else "<empty>"
