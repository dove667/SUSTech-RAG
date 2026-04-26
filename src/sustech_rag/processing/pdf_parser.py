from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: Path) -> str:
    # 目前默认 crawl 配置不会抓取 PDF，这段解析逻辑暂未在当前数据流程中实际使用，
    # 但保留为后续单独启用 PDF 支持时的实现基础。
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()
