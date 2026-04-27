from __future__ import annotations

import os
from pathlib import Path

import pytest

from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    EmbeddingConfig,
    LLMConfig,
    LocalLLMConfig,
    ProcessingConfig,
    ProjectConfig,
    RetrievalConfig,
    VectorStoreConfig,
)


def _make_config(tmp_path: Path, batch_size: int = 4) -> AppConfig:
    local_embedding_dir = Path("data/models/embeddings/BAAI/bge-small-zh-v1.5")
    local_embedding_path = str(local_embedding_dir) if local_embedding_dir.exists() else ""
    return AppConfig(
        project=ProjectConfig(name="test", data_dir=tmp_path),
        crawl=CrawlConfig(
            user_agent="test-agent",
            seed_urls=["https://example.com"],
            allowed_domains=["example.com"],
        ),
        processing=ProcessingConfig(),
        embedding=EmbeddingConfig(
            model_name="BAAI/bge-small-zh-v1.5",
            local_path=local_embedding_path,
            batch_size=batch_size,
        ),
        retrieval=RetrievalConfig(reranker_model="BAAI/bge-reranker-v2-m3"),
        vector_store=VectorStoreConfig(
            persist_dir=tmp_path / "vector_store",
            collection_name="test-collection",
        ),
        llm=LLMConfig(
            local=LocalLLMConfig(),
        ),
    )


class TestIndexing:
    """Indexing integration tests. Requires embedding model to be cached."""

    @pytest.fixture(autouse=True)
    def _check_model(self) -> None:
        if not Path("data/models/embeddings/BAAI/bge-small-zh-v1.5").exists():
            pytest.skip("Embedding model not cached")
        os.environ["HF_HUB_OFFLINE"] = "1"

    def test_index_inserts_all_chunks(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl

        interim = ensure_dir(tmp_path / "interim")
        chunks = [
            {
                "chunk_id": f"chunk-{i}",
                "doc_id": "doc-1",
                "title": "Test",
                "text": f"Chunk text number {i} with some content here.",
                "source_url": "https://example.com/",
            }
            for i in range(10)
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)

        from sustech_rag.indexing.vector_index import build_vector_index

        config = _make_config(tmp_path, batch_size=8)
        build_vector_index(config, rebuild=True)

        import chromadb

        client = chromadb.PersistentClient(path=str(tmp_path / "vector_store"))
        coll = client.get_collection("test-collection")
        assert coll.count() == 10

    def test_rebuild_replaces_collection(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl

        interim = ensure_dir(tmp_path / "interim")
        chunks = [
            {
                "chunk_id": "chunk-0",
                "doc_id": "doc-1",
                "title": "Test",
                "text": "Initial chunk.",
                "source_url": "https://example.com/",
            }
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)

        import chromadb

        config = _make_config(tmp_path)
        chroma_path = str(tmp_path / "vector_store")

        from sustech_rag.indexing.vector_index import build_vector_index

        build_vector_index(config, rebuild=False)
        client = chromadb.PersistentClient(path=chroma_path)
        coll = client.get_collection("test-collection")
        assert coll.count() == 1

        chunks = [
            {
                "chunk_id": "chunk-new",
                "doc_id": "doc-2",
                "title": "New",
                "text": "New chunk after rebuild.",
                "source_url": "https://example.com/new",
            }
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)

        build_vector_index(config, rebuild=True)
        coll = client.get_collection("test-collection")
        assert coll.count() == 1

        results = coll.get()
        assert len(results["documents"]) == 1
        assert results["documents"][0] == "New chunk after rebuild."

    def test_empty_chunks_returns_index(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl

        interim = ensure_dir(tmp_path / "interim")
        write_jsonl(interim / "chunks.jsonl", [])

        from sustech_rag.indexing.vector_index import build_vector_index

        config = _make_config(tmp_path)
        index = build_vector_index(config, rebuild=True)

        assert index is not None