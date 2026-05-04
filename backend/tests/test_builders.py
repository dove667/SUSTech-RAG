from pathlib import Path

from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    EmbeddingConfig,
    LocalLLMConfig,
    ProcessingConfig,
    ProjectConfig,
    RetrievalConfig,
    VectorStoreConfig,
)
from sustech_rag.pipeline.builders import build_chunks, preprocess_documents
from sustech_rag.utils.io import read_jsonl, write_jsonl


def _make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        project=ProjectConfig(name="test-rag", data_dir=tmp_path),
        crawl=CrawlConfig(
            user_agent="test-agent",
            seed_urls=["https://example.com"],
            allowed_domains=["example.com"],
        ),
        processing=ProcessingConfig(
            min_text_length=20,
            max_repeated_line_ratio=0.35,
            drop_patterns=["版权所有"],
            chunk_size=80,
            chunk_overlap=10,
        ),
        embedding=EmbeddingConfig(model_name="dummy"),
        retrieval=RetrievalConfig(reranker_model="dummy"),
        vector_store=VectorStoreConfig(
            persist_dir=tmp_path / "vector_store",
            collection_name="test-collection",
        ),
        llm=LocalLLMConfig(),
    )


def test_preprocess_documents_prefixes_title_and_build_chunks(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    raw_path = tmp_path / "raw" / "raw_documents.jsonl"
    write_jsonl(
        raw_path,
        [
            {
                "doc_id": "doc-1",
                "url": "https://example.com/notice",
                "title": "课程报名通知",
                "content_type": "text/html",
                "text": "请同学们于本周内完成报名。\n版权所有 SUSTech",
                "source_path": str(tmp_path / "raw" / "doc-1.html"),
                "metadata": {"parser": "readability_lxml"},
            }
        ],
    )

    docs = preprocess_documents(config)

    assert len(docs) == 1
    assert docs[0].text == "课程报名通知\n请同学们于本周内完成报名。"

    cleaned_rows = read_jsonl(tmp_path / "interim" / "documents.cleaned.jsonl")
    assert cleaned_rows[0]["text"] == "课程报名通知\n请同学们于本周内完成报名。"

    chunks = build_chunks(config)
    assert chunks
    assert chunks[0].text.startswith("课程报名通知")
