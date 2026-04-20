from __future__ import annotations

from pathlib import Path

from sustech_rag.config.models import AppConfig
from sustech_rag.crawlers.site_crawler import SiteCrawler
from sustech_rag.pipeline.schemas import ChunkedDocument, RawDocument
from sustech_rag.processing.chunking import chunk_document
from sustech_rag.processing.cleaning import clean_text, is_high_quality
from sustech_rag.processing.pdf_parser import extract_pdf_text
from sustech_rag.utils.io import read_jsonl, write_jsonl


def crawl_documents(config: AppConfig) -> list[RawDocument]:
    crawler = SiteCrawler(config.crawl, config.project.data_dir)
    docs = crawler.crawl()
    write_jsonl(_raw_manifest_path(config), [doc.to_dict() for doc in docs])
    return docs


def preprocess_documents(config: AppConfig) -> list[RawDocument]:
    rows = read_jsonl(_raw_manifest_path(config))
    docs: list[RawDocument] = []
    for row in rows:
        doc = RawDocument(**row)
        if doc.content_type == "application/pdf":
            doc.text = extract_pdf_text(Path(doc.source_path))
        doc.text = clean_text(doc.text, config.processing)
        if is_high_quality(doc, config.processing):
            docs.append(doc)
    write_jsonl(_clean_docs_path(config), [doc.to_dict() for doc in docs])
    return docs


def build_chunks(config: AppConfig) -> list[ChunkedDocument]:
    rows = read_jsonl(_clean_docs_path(config))
    docs = [RawDocument(**row) for row in rows]
    chunks: list[ChunkedDocument] = []
    for doc in docs:
        chunks.extend(
            chunk_document(
                doc,
                chunk_size=config.processing.chunk_size,
                chunk_overlap=config.processing.chunk_overlap,
            )
        )
    write_jsonl(_chunks_path(config), [chunk.to_dict() for chunk in chunks])
    return chunks


def _raw_manifest_path(config: AppConfig) -> Path:
    return config.project.data_dir / "raw" / "raw_documents.jsonl"


def _clean_docs_path(config: AppConfig) -> Path:
    return config.project.data_dir / "interim" / "documents.cleaned.jsonl"


def _chunks_path(config: AppConfig) -> Path:
    return config.project.data_dir / "interim" / "chunks.jsonl"
