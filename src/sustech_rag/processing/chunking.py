from __future__ import annotations

import re

from llama_index.core.node_parser import SentenceSplitter

from sustech_rag.pipeline.schemas import ChunkedDocument, RawDocument


def chunk_document(doc: RawDocument, chunk_size: int, chunk_overlap: int) -> list[ChunkedDocument]:
    """
    将原始文档按段落优先切分为多个 chunk，并保留来源元信息。
    输入参数：
    - doc: 待切分的原始文档。
    - chunk_size: 每个分块的目标大小。
    - chunk_overlap: 分块之间的重叠长度。
    输出参数：
    - 返回分块后的文档列表。
    """
    if not doc.text.strip():
        return []

    if _is_structured_short_page(doc.text, chunk_size, chunk_overlap):
        chunk_texts = [doc.text.strip()]
    else:
        chunk_texts = _split_text_by_paragraphs(doc.text, chunk_size, chunk_overlap)
        chunk_texts = _merge_short_chunks(chunk_texts, chunk_size)

    results: list[ChunkedDocument] = []
    for index, chunk in enumerate(chunk_texts):
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


def _split_text_by_paragraphs(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    先按段落聚合文本，再对超长段落执行句级切分。
    输入参数：
    - text: 已清洗的文档正文。
    - chunk_size: 每个分块的目标大小。
    - chunk_overlap: 分块之间的重叠长度。
    输出参数：
    - 返回初步切分后的文本块列表。
    """
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    if not paragraphs:
        return []

    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks: list[str] = []
    pending: list[str] = []
    pending_length = 0

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if pending:
                chunks.append("\n\n".join(pending))
                pending = []
                pending_length = 0
            chunks.extend(splitter.split_text(paragraph))
            continue

        separator_length = 2 if pending else 0
        next_length = pending_length + separator_length + len(paragraph)
        if pending and next_length > chunk_size:
            chunks.append("\n\n".join(pending))
            pending = [paragraph]
            pending_length = len(paragraph)
            continue

        pending.append(paragraph)
        pending_length = next_length

    if pending:
        chunks.append("\n\n".join(pending))
    return chunks


def _merge_short_chunks(chunks: list[str], chunk_size: int) -> list[str]:
    """
    合并过短文本块，减少信息过于稀疏的尾部 chunk。
    输入参数：
    - chunks: 初步切分后的文本块列表。
    - chunk_size: 每个分块的目标大小。
    输出参数：
    - 返回合并后的文本块列表。
    """
    if not chunks:
        return []

    min_chunk_length = max(120, chunk_size // 3)
    max_merged_length = int(chunk_size * 1.35)
    merged: list[str] = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        if len(chunk) < min_chunk_length and merged:
            candidate = f"{merged[-1]}\n\n{chunk}"
            if len(candidate) <= max_merged_length:
                merged[-1] = candidate
                continue

        merged.append(chunk)

    if len(merged) >= 2 and len(merged[-1]) < min_chunk_length:
        candidate = f"{merged[-2]}\n\n{merged[-1]}"
        if len(candidate) <= max_merged_length:
            merged[-2] = candidate
            merged.pop()

    return merged


def _is_structured_short_page(text: str, chunk_size: int, chunk_overlap: int) -> bool:
    """
    判断文本是否适合整体保留为单个结构化短页 chunk。
    输入参数：
    - text: 已清洗的文档正文。
    - chunk_size: 每个分块的目标大小。
    - chunk_overlap: 分块之间的重叠长度。
    输出参数：
    - 若文本属于结构化短页则返回 True，否则返回 False。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    max_length = max(chunk_size + chunk_overlap, int(chunk_size * 1.5))
    if len(text) > max_length:
        return False

    structured_lines = sum(1 for line in lines if _is_structured_line(line))
    return structured_lines >= max(2, len(lines) // 2)


def _is_structured_line(line: str) -> bool:
    """
    判断单行是否更像时间地点等结构化字段，而非普通段落。
    输入参数：
    - line: 单行文本。
    输出参数：
    - 若该行是结构化字段则返回 True，否则返回 False。
    """
    if len(line) > 64:
        return False
    if re.search(r"(时间|地点|主讲|嘉宾|报名|联系人|邮箱|电话|链接|日期|地址)", line):
        return True
    if "：" in line or ":" in line:
        return True
    if re.search(r"\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?", line):
        return True
    return False
