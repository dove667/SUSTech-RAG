from backend.src.sustech_rag.config.loader import load_config
from backend.src.sustech_rag.indexing.vector_index import build_vector_index
from backend.src.sustech_rag.pipeline.builders import build_chunks, crawl_documents, preprocess_documents


def main() -> None:
    config = load_config()
    crawl_documents(config)
    preprocess_documents(config)
    build_chunks(config)
    build_vector_index(config)


if __name__ == "__main__":
    main()
