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
    "你是南方科技大学校园知识库问答系统的请求路由器。"
    "你的任务只有一个：判断用户请求是否属于南方科技大学校园知识库的服务范围。"
    "如果请求需要查询、核实、引用或回答与南方科技大学相关的事实信息，"
    "就设置 should_retrieve=true。"
    "如果请求与南方科技大学无关，或者不是南方科技大学校园知识库应处理的问题，"
    "就设置 should_retrieve=false。"
    "输出必须是单个 JSON 对象，不要输出 Markdown，不要输出代码块。"
)

_RELEVANCE_SYSTEM_PROMPT = (
    "你是一个严格的检索过滤器。"
    "只有当候选文档能直接支持回答用户问题时，才标记为相关。"
    "仅仅共享关键词、只提到同名实体、或者只有很弱的间接关联，都应标记为不相关。"
    "输出必须是单个 JSON 对象，不要输出 Markdown，不要输出代码块。"
)

_SUPPORT_SYSTEM_PROMPT = (
    "你是一个严格的事实支持性审查器。"
    "请判断候选回答中的关键事实是否都能被提供的证据片段直接支持。"
    "如果回答包含证据中没有明确给出的关键信息、推断过度、范围扩大或措辞过满，就视为不充分支持。"
    "输出必须是单个 JSON 对象，不要输出 Markdown，不要输出代码块。"
)

# ---------------------------------------------------------------------------
# JSON schemas for structured / constrained generation
# ---------------------------------------------------------------------------

_ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "should_retrieve": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["should_retrieve"],
}

_RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_index": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["candidate_index", "relevant"],
            },
        },
    },
    "required": ["assessments"],
}

_SUPPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "supported": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["supported"],
}

class SelfRAGController:
    """负责 self-RAG 的检索判定、文档过滤与答案支持性判断。"""

    def __init__(self, llm: LLMClient, max_rounds: int) -> None:
        self._llm = llm
        self.max_rounds = max(1, max_rounds)

    def should_retrieve(self, query: str, history: list[dict]) -> RetrievalDecision:
        history_text = self._format_history(history)
        user_prompt = (
            "请判断下面这个请求是否属于南方科技大学校园知识库的服务范围。\n"
            "规则：\n"
            "- 若问题需要南方科技大学相关事实、政策、机构、课程、活动、人物、地点、时间等信息，"
            "should_retrieve=true。\n"
            "- 若请求与南方科技大学无关，或者不属于校园知识库问答应处理的请求，"
            "should_retrieve=false。\n"
            f"对话历史：\n{history_text}\n\n"
            f"用户问题：{query}\n\n"
            '输出 JSON，格式为 {"should_retrieve": true, "reason": "..."}。'
        )
        data = self._generate_json(_ROUTER_SYSTEM_PROMPT, user_prompt, _ROUTER_SCHEMA)
        return RetrievalDecision(
            should_retrieve=self._parse_bool(data.get("should_retrieve"), default=True),
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
            '输出 JSON，格式为 '
            '{"assessments": [{"candidate_index": 1, "relevant": true, "reason": "..."}]}。'
        )
        data = self._generate_json(_RELEVANCE_SYSTEM_PROMPT, user_prompt, _RELEVANCE_SCHEMA)
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
                        relevant=self._parse_bool(raw_item.get("relevant"), default=False),
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
        data = self._generate_json(_SUPPORT_SYSTEM_PROMPT, user_prompt, _SUPPORT_SCHEMA)
        return SupportDecision(
            supported=self._parse_bool(data.get("supported"), default=False),
            reason=str(data.get("reason", "")),
        )

    def _generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict | None = None,
    ) -> dict[str, object]:
        # 优先使用结构化 / 约束生成
        if schema is not None and hasattr(self._llm, "generate_with_schema"):
            try:
                result = self._llm.generate_with_schema(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    schema,
                )
                if result:  # 非空 dict 视为成功
                    return result
            except Exception:
                pass  # 回退到 prompt 模式

        # 回退：通过 prompt 要求 JSON 输出
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
    def _parse_bool(value: object, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "true":
                return True
            if normalized == "false":
                return False
        return default


    @staticmethod
    def _format_history(history: list[dict]) -> str:
        entries = []
        for item in history[-6:]:
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "").strip()
            if content:
                entries.append(f"{role}: {content}")
        return "\n".join(entries) if entries else "<empty>"
