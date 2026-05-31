from pathlib import Path

import yaml

from sustech_rag.config.loader import load_config
from sustech_rag.config.models import LlamaCppConfig, VLLMConfig


def test_load_config() -> None:
    config = load_config("configs/default.yaml")
    assert config.project.name == "sustech-campus-rag"
    assert config.embedding.model_name == "BAAI/bge-small-zh-v1.5"
    assert config.processing.min_text_length == 60
    assert str(config.embedding.local_path).endswith(
        "data/models/embeddings/BAAI/bge-small-zh-v1.5"
    )
    assert str(config.retrieval.reranker_local_path).endswith(
        "data/models/rerankers/BAAI/bge-reranker-v2-m3"
    )
    assert str(config.vector_store.persist_dir).endswith("data/vector_store/chroma")
    assert isinstance(config.llm, LlamaCppConfig)
    assert str(config.llm.model_path).endswith("data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf")


def test_load_vllm_config_preserves_absolute_and_home_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    project_dir = tmp_path / "project"
    config_dir = project_dir / "configs"
    config_dir.mkdir(parents=True)
    absolute_model_dir = tmp_path / "models" / "qwen"
    absolute_model_dir.mkdir(parents=True)

    payload = {
        "project": {"name": "demo", "data_dir": "data"},
        "crawl": {
            "user_agent": "ua",
            "seed_urls": ["https://example.com"],
            "allowed_domains": ["example.com"],
        },
        "processing": {},
        "embedding": {"model_name": "embed"},
        "retrieval": {"reranker_model": "reranker"},
        "vector_store": {"persist_dir": "data/vector_store/chroma", "collection_name": "kb"},
        "llm": {
            "backend": "vllm",
            "model_name": "",
            "local_path": str(absolute_model_dir),
            "binary_path": "~/miniconda3/envs/vllm-0.21/bin/vllm",
        },
    }
    config_path = config_dir / "vllm.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    config = load_config(str(config_path))

    assert isinstance(config.llm, VLLMConfig)
    assert config.llm.local_path == str(absolute_model_dir.resolve())
    assert config.llm.binary_path == str(
        (home_dir / "miniconda3" / "envs" / "vllm-0.21" / "bin" / "vllm").resolve()
    )
