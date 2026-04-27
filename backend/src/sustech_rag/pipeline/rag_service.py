from __future__ import annotations

from sustech_rag.config.models import AppConfig
from sustech_rag.llm.backends import LlamaCppBackend
from sustech_rag.retrieval.engine import RetrievalEngine


class RagService:
    """
    封装检索与大模型生成的问答服务。
    """

    def __init__(self, config: AppConfig) -> None:
        """
        初始化问答服务所需的检索器与大模型后端。
        输入参数：
            config: 应用配置对象。
        输出参数：
            无。
        """
        self.config = config
        self.retrieval = RetrievalEngine(config)
        self.llm = LlamaCppBackend(config)

    def answer(self, query: str) -> str:
        """
        基于检索上下文生成中文问答结果。
        输入参数：
            query: 用户提问内容。
        输出参数：
            str: 大模型生成的回答文本。
        """
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
