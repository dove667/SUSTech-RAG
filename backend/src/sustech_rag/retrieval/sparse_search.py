from __future__ import annotations

from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

from sustech_rag.retrieval.reranker import RetrievedChunk
from sustech_rag.utils.io import read_jsonl


class BM25Searcher:
    """基于 BM25 的稀疏关键词检索引擎。

    在初始化时从 chunks.jsonl 加载语料，构建 BM25 内存索引。
    jieba 分词负责中文切词，英文/数字由 jieba 自动保留为独立 token。
    """

    def __init__(self, chunks_path: str, top_k: int = 8) -> None:
        rows = read_jsonl(Path(chunks_path))
        if not rows:
            raise FileNotFoundError(f"no chunks found in {chunks_path}")

        self._metadata: list[dict] = []
        corpus: list[list[str]] = []
        for row in rows:
            text = row.get("text", "")
            self._metadata.append(
                {
                    "text": text,
                    "title": row.get("title", "Untitled"),
                    "source_url": row.get("source_url", ""),
                    "score": 0.0,
                }
            )
            tokens = list(jieba.lcut(text))
            corpus.append(tokens)

        self._index = BM25Okapi(corpus)
        self.top_k = top_k

    def search(self, query: str) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        tokens = list(jieba.lcut(query))
        scores = self._index.get_scores(tokens)
        # 手动取 top_k: 找出 scores 最高的 k 个索引
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[RetrievedChunk] = []
        for idx, score in indexed[: self.top_k]:
            meta = self._metadata[idx]
            results.append(
                RetrievedChunk(
                    text=meta["text"],
                    score=float(score),
                    metadata={
                        "title": meta["title"],
                        "source_url": meta["source_url"],
                    },
                )
            )
        return results
