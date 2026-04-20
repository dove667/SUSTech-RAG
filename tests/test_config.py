from sustech_rag.config.loader import load_config


def test_load_config() -> None:
    config = load_config("configs/default.yaml")
    assert config.project.name == "sustech-campus-rag"
    assert config.embedding.model_name == "BAAI/bge-small-zh-v1.5"
