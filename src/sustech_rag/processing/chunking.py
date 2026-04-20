from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter

from sustech_rag.pipeline.schemas import ChunkedDocument, RawDocument


def chunk_document(doc: RawDocument, chunk_size: int, chunk_overlap: int) -> list[ChunkedDocument]:
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
