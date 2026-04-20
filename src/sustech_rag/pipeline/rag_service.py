from __future__ import annotations

from sustech_rag.config.models import AppConfig
from sustech_rag.llm.backends import build_llm_backend
from sustech_rag.retrieval.engine import RetrievalEngine


class RagService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.retrieval = RetrievalEngine(config)
        self.llm = build_llm_backend(config)

    def answer(self, query: str) -> str:
        chunks = self.retrieval.retrieve(query)
        context = "\n\n".join(
            f"[{idx + 1}] {chunk.metadata.get('title', 'Untitled')}\n{chunk.text}"
            for idx, chunk in enumerate(chunks)
        )
        prompt = (
            "你是南方科技大学校园知识库问答助手。请基于提供的检索上下文回答问题，"
            "如果上下文不足，请明确说明。\n\n"
            f"问题：{query}\n\n"
            f"上下文：\n{context}\n\n"
            "请给出简洁、准确的中文回答，并尽量引用信息来源标题。"
        )
        return self.llm.generate(prompt)
