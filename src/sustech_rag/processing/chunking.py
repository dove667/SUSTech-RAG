from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter

from sustech_rag.pipeline.schemas import ChunkedDocument, RawDocument


def chunk_document(doc: RawDocument, chunk_size: int, chunk_overlap: int) -> list[ChunkedDocument]:
    """
    将原始文档按句子切分为多个 chunk，并保留来源元信息。
    输入参数：
    - doc: 待切分的原始文档。
    - chunk_size: 每个分块的目标大小。
    - chunk_overlap: 分块之间的重叠长度。
    输出参数：
    - 返回分块后的文档列表。
    """
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_text(doc.text)
    results: list[ChunkedDocument] = []
    for index, chunk in enumerate(chunks):
        results.append(
            ChunkedDocument(
                chunk_id=f"{doc.doc_id}-{index}",
                doc_id=doc.doc_id,
                text=chunk,
                source_url=doc.url,
                title=doc.title,
                metadata=doc.metadata,
            )
        )
    return results
