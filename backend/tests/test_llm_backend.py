from __future__ import annotations

from pathlib import Path

from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    EmbeddingConfig,
    ProcessingConfig,
    ProjectConfig,
    RetrievalConfig,
    VectorStoreConfig,
    VLLMConfig,
)
from sustech_rag.llm.backends import LlamaCppBackend
from sustech_rag.llm.factory import create_llm_backend
from sustech_rag.llm.vllm_backend import VLLMBackend


def _backend_with_runtime_options(device_mode: str, gpu_layers: str = "32") -> LlamaCppBackend:
    backend = object.__new__(LlamaCppBackend)
    backend._device_mode = device_mode
    backend._device_name = ""
    backend._gpu_layers = gpu_layers
    backend._threads = 0
    backend._threads_batch = 0
    backend._reasoning = "off"
    return backend


def test_metal_mode_uses_implicit_llama_cpp_device_selection() -> None:
    backend = _backend_with_runtime_options("metal")

    assert backend._build_runtime_args() == ["-ngl", "32", "--reasoning", "off"]


def test_cpu_mode_disables_device_offload() -> None:
    backend = _backend_with_runtime_options("cpu", gpu_layers="0")

    assert backend._build_runtime_args() == ["--device", "none", "-ngl", "0", "--reasoning", "off"]


def test_factory_selects_vllm_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        "sustech_rag.utils.runtime.ensure_vllm_binary",
        lambda _: "/usr/local/bin/vllm",
    )
    config = AppConfig(
        project=ProjectConfig(name="demo", data_dir=Path("data")),
        crawl=CrawlConfig(
            user_agent="ua",
            seed_urls=["https://example.com"],
            allowed_domains=["example.com"],
        ),
        processing=ProcessingConfig(),
        embedding=EmbeddingConfig(model_name="embed"),
        retrieval=RetrievalConfig(reranker_model="reranker"),
        vector_store=VectorStoreConfig(
            persist_dir=Path("data/vector_store/chroma"),
            collection_name="test",
        ),
        llm=VLLMConfig(
            backend="vllm",
            model_name="Qwen/Qwen3-8B",
            binary_path="/opt/vllm-0.21.0/bin/vllm",
        ),
    )

    backend = create_llm_backend(config)

    assert isinstance(backend, VLLMBackend)


def test_ensure_vllm_binary_accepts_explicit_path(tmp_path) -> None:
    from sustech_rag.utils.runtime import ensure_vllm_binary

    binary = tmp_path / "vllm"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")

    assert ensure_vllm_binary(str(binary)) == str(binary.resolve())


def test_vllm_runtime_args_include_multi_gpu_options() -> None:
    backend = object.__new__(VLLMBackend)
    backend._host = "127.0.0.1"
    backend._port = 8081
    backend._vllm = VLLMConfig(
        model_name="Qwen/Qwen3-32B",
        served_model_name="qwen3-32b",
        dtype="float16",
        gpu_memory_utilization=0.92,
        tensor_parallel_size=4,
        pipeline_parallel_size=1,
        data_parallel_size=1,
        distributed_executor_backend="mp",
        max_model_len=32768,
        max_num_seqs=64,
        max_num_batched_tokens=16384,
        generation_config="vllm",
        enable_prefix_caching=True,
        disable_uvicorn_access_log=True,
        max_parallel_loading_workers=4,
    )

    args = backend._build_runtime_args()

    assert "--tensor-parallel-size" in args
    assert args[args.index("--tensor-parallel-size") + 1] == "4"
    assert "--distributed-executor-backend" in args
    assert args[args.index("--distributed-executor-backend") + 1] == "mp"
    assert "--served-model-name" in args
    assert args[args.index("--served-model-name") + 1] == "qwen3-32b"
