from __future__ import annotations

from pathlib import Path

from backend.src.sustech_rag.config.models import AppConfig
from backend.src.sustech_rag.crawlers.site_crawler import SiteCrawler
from backend.src.sustech_rag.pipeline.schemas import ChunkedDocument, RawDocument
from backend.src.sustech_rag.processing.chunking import chunk_document
from backend.src.sustech_rag.processing.cleaning import build_effective_text, is_high_quality
from backend.src.sustech_rag.processing.pdf_parser import extract_pdf_text
from backend.src.sustech_rag.utils.io import read_jsonl, write_jsonl


def crawl_documents(config: AppConfig) -> list[RawDocument]:
    """
    抓取站点文档并写入原始文档清单。
    输入参数：
        config: 应用配置对象。
    输出参数：
        list[RawDocument]: 抓取到的原始文档列表。
    """
    crawler = SiteCrawler(config.crawl, config.project.data_dir)
    docs = crawler.crawl()
    write_jsonl(_raw_manifest_path(config), [doc.to_dict() for doc in docs])
    return docs


def preprocess_documents(config: AppConfig) -> list[RawDocument]:
    """
    读取原始文档并执行清洗、过滤与文本重建。
    输入参数：
        config: 应用配置对象。
    输出参数：
        list[RawDocument]: 预处理后保留的原始文档列表。
    """
    rows = read_jsonl(_raw_manifest_path(config))
    docs: list[RawDocument] = []
    for row in rows:
        doc = RawDocument(**row)
        # PDF 预处理路径保留着，但当前默认配置已关闭 PDF 抓取，因此通常不会进入这里。
        if doc.content_type == "application/pdf":
            doc.text = extract_pdf_text(Path(doc.source_path))
        doc.text = build_effective_text(doc.title, doc.text, config.processing)
        if is_high_quality(doc, config.processing):
            docs.append(doc)
    write_jsonl(_clean_docs_path(config), [doc.to_dict() for doc in docs])
    return docs


def build_chunks(config: AppConfig) -> list[ChunkedDocument]:
    """
    将清洗后的文档切分为文本块并持久化结果。
    输入参数：
        config: 应用配置对象。
    输出参数：
        list[ChunkedDocument]: 生成的文本块列表。
    """
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
    """
    构造原始文档清单文件路径。
    输入参数：
        config: 应用配置对象。
    输出参数：
        Path: 原始文档清单文件路径。
    """
    return config.project.data_dir / "raw" / "raw_documents.jsonl"


def _clean_docs_path(config: AppConfig) -> Path:
    """
    构造清洗后文档文件路径。
    输入参数：
        config: 应用配置对象。
    输出参数：
        Path: 清洗后文档文件路径。
    """
    return config.project.data_dir / "interim" / "documents.cleaned.jsonl"


def _chunks_path(config: AppConfig) -> Path:
    """
    构造文本块输出文件路径。
    输入参数：
        config: 应用配置对象。
    输出参数：
        Path: 文本块输出文件路径。
    """
    return config.project.data_dir / "interim" / "chunks.jsonl"
