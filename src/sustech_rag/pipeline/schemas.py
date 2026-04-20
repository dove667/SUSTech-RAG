from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class RawDocument:
    doc_id: str
    url: str
    title: str
    content_type: str
    text: str
    source_path: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ChunkedDocument:
    chunk_id: str
    doc_id: str
    text: str
    source_url: str
    title: str
    metadata: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)
