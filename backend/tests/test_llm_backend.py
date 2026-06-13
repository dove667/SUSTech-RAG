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
from sustech_rag.llm.base import OpenAICompatibleEndpoint
from sustech_rag.llm.factory import create_llm_runtime
from sustech_rag.llm.llama_cpp import LlamaCppLauncher
from sustech_rag.llm.vllm import VLLMClient, VLLMLauncher
from sustech_rag.utils.runtime import resolve_torch_dtype


def _launcher_with_runtime_options(device_mode: str, gpu_layers: str = "32") -> LlamaCppLauncher:
    launcher = object.__new__(LlamaCppLauncher)
    launcher._device_mode = device_mode
    launcher._device_name = ""
    launcher._gpu_layers = gpu_layers
    launcher._threads = None
    launcher._threads_batch = None
    launcher._reasoning_parser = ""
    launcher._flash_attn = "auto"
    launcher._ubatch_size = 512
    launcher._cache_type_k = "q8_0"
    launcher._cache_type_v = "q8_0"
    launcher._kv_offload = True
    launcher._n_batch = 512
    return launcher


def test_metal_mode_uses_implicit_llama_cpp_device_selection() -> None:
    launcher = _launcher_with_runtime_options("metal")

    assert launcher._build_runtime_args() == [
        "-ngl", "32",
        "--flash-attn", "auto",
        "--ubatch-size", "512",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--kv-offload",
        "-b", "512",
    ]


def test_cpu_mode_disables_device_offload() -> None:
    launcher = _launcher_with_runtime_options("cpu", gpu_layers="0")

    assert launcher._build_runtime_args() == [
        "--device", "none",
        "-ngl", "0",
        "--flash-attn", "auto",
        "--ubatch-size", "512",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--kv-offload",
        "-b", "512",
    ]


def test_factory_builds_vllm_runtime() -> None:
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
            local_path="/models/Qwen3-8B",
            served_model_name="qwen3-8b",
        ),
    )

    runtime = create_llm_runtime(config)

    assert isinstance(runtime.client, VLLMClient)
    assert isinstance(runtime.launcher, VLLMLauncher)


def test_vllm_runtime_args_include_multi_gpu_options() -> None:
    launcher = object.__new__(VLLMLauncher)
    launcher._endpoint = OpenAICompatibleEndpoint(
        host="127.0.0.1",
        port=8081,
        model_path="/models/Qwen3-32B",
        served_model_name="qwen3-32b",
    )
    launcher._vllm = VLLMConfig(
        local_path="/models/Qwen3-32B",
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

    args = launcher._build_runtime_args()

    assert "--tensor-parallel-size" in args
    assert args[args.index("--tensor-parallel-size") + 1] == "4"
    assert "--distributed-executor-backend" in args
    assert args[args.index("--distributed-executor-backend") + 1] == "mp"
    assert "--served-model-name" in args
    assert args[args.index("--served-model-name") + 1] == "qwen3-32b"


def test_resolve_torch_dtype_supports_bf16_aliases() -> None:
    import torch

    assert resolve_torch_dtype("bf16") == torch.bfloat16
    assert resolve_torch_dtype("bfloat16") == torch.bfloat16
    assert resolve_torch_dtype("") is None
