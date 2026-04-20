from __future__ import annotations

from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    score: float
    metadata: dict


class BGECrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = CrossEncoder(model_name, trust_remote_code=True)

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_n: int) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [[query, item.text] for item in candidates]
        scores = self.model.predict(pairs)
        ranked = sorted(
            (
                RetrievedChunk(text=item.text, score=float(score), metadata=item.metadata)
                for item, score in zip(candidates, scores, strict=True)
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked[:top_n]
