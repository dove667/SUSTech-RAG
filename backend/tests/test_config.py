from sustech_rag.config.loader import load_config


def test_load_config() -> None:
    config = load_config("configs/default.yaml")
    assert config.project.name == "sustech-campus-rag"
    assert config.embedding.model_name == "BAAI/bge-small-zh-v1.5"
    assert config.processing.min_text_length == 60
    assert str(config.embedding.local_path).endswith("data/models/embeddings/BAAI/bge-small-zh-v1.5")
    assert str(config.retrieval.reranker_local_path).endswith(
        "data/models/rerankers/BAAI/bge-reranker-v2-m3"
    )
    assert str(config.vector_store.persist_dir).endswith("data/vector_store/chroma")
    assert str(config.llm.local.model_path).endswith("data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf")
