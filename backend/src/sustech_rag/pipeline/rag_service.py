from __future__ import annotations

from collections.abc import Iterator

from sustech_rag.config.models import AppConfig
from sustech_rag.llm.backends import build_llm_backend
from sustech_rag.retrieval.engine import RetrievalEngine
from sustech_rag.retrieval.reranker import RetrievedChunk

_DEFAULT_SYSTEM_PROMPT = (
    "你是校园知识库问答助手。请基于提供的检索上下文回答问题，"
    "如果上下文不足，请明确说明。请给出简洁、准确的中文回答，并尽量引用信息来源标题。"
)


class RagService:
    """封装检索与大模型生成的问答服务。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.retrieval = RetrievalEngine(config)
        self.llm = build_llm_backend(config)

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
        # Ensure the last message is the user query
        if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != query:
            messages.append({"role": "user", "content": query})
        return messages

    def _extract_last_user_query(self, messages: list[dict]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user" and (m.get("content") or "").strip():
                return m["content"].strip()
        raise ValueError("no user message found in conversation")

    def answer(self, query: str) -> str:
        chunks = self.retrieval.retrieve(query)
        msgs = self._build_chat_messages(query, chunks, [])
        # build a plain prompt from messages for generate()
        prompt = "\n".join(
            f"<|{m['role']}|>\n{m['content']}" for m in msgs
        ) + "\n<|assistant|>\n"
        return self.llm.generate(prompt)

    def answer_with_chunks(self, query: str) -> tuple[list[RetrievedChunk], str]:
        chunks = self.retrieval.retrieve(query)
        answer = self.answer(query)
        return chunks, answer

    def answer_stream(self, messages: list[dict]) -> Iterator[tuple[str, object]]:
        """Retrieve and stream. Yields (event_type, data):
        - ("reference", list[RetrievedChunk])
        - ("think.delta", str)
        - ("think.end", None)
        - ("content.delta", str)
        """
        query = self._extract_last_user_query(messages)
        chunks = self.retrieval.retrieve(query)

        if chunks:
            yield ("reference", chunks)

        # Build conversation history (all messages before the last user query)
        history = [m for m in messages if m.get("content", "").strip()]
        # Remove the last message (current query) from history since it's the query
        if history and history[-1].get("content", "").strip() == query:
            history = history[:-1]

        chat_messages = self._build_chat_messages(query, chunks, history)

        think_open = False
        for event_type, text in self.llm.generate_stream(chat_messages):
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

    def health_check(self) -> dict:
        components = {}
        try:
            _ = self.retrieval.index
            components["retrieval"] = "ok"
        except Exception as exc:
            components["retrieval"] = str(exc)

        llm_ok, llm_msg = self.llm.verify()
        components["llm"] = llm_msg

        all_ok = all(v == "ok" for v in components.values())
        return {
            "status": "ready" if all_ok else "error",
            "components": components,
        }
