"""Run the full RAG pipeline (crawl → preprocess → index) as a single script.

Prefer the CLI for interactive use::

    uv run sustech-rag crawl
    uv run sustech-rag preprocess
    uv run sustech-rag index
"""

from __future__ import annotations

from sustech_rag.config.loader import load_config
from sustech_rag.indexing.vector_index import build_vector_index
from sustech_rag.pipeline.builders import build_chunks, crawl_documents, preprocess_documents


def main() -> None:
    config = load_config()
    crawl_documents(config)
    preprocess_documents(config)
    build_chunks(config)
    build_vector_index(config)


if __name__ == "__main__":
    main()
