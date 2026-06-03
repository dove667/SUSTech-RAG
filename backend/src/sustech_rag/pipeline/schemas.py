from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sustech_rag.retrieval.reranker import RetrievedChunk


@dataclass(slots=True)
class RawDocument:
    """
    描述抓取阶段的原始文档数据结构。
    """

    doc_id: str
    url: str
    title: str
    content_type: str
    text: str
    source_path: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        将原始文档转换为字典形式。
        """
        return asdict(self)


@dataclass(slots=True)
class ChunkedDocument:
    """
    描述文本分块阶段生成的块数据结构。
    """

    chunk_id: str
    doc_id: str
    text: str
    source_url: str
    title: str
    metadata: dict[str, str]

    def to_dict(self) -> dict:
        """
        将文本块转换为字典形式。
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RetrievalDecision:
    should_retrieve: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ChunkRelevanceDecision:
    candidate_index: int
    relevant: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class SupportDecision:
    supported: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class AnswerPlan:
    chunks: list[RetrievedChunk]
    requires_retrieval: bool
    system_prompt: str = ""
    debug_events: list[SelfRAGDebugEvent] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SelfRAGDebugEvent:
    event: str
    payload: dict
