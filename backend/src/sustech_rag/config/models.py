from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ProjectConfig(BaseModel):
    name: str
    data_dir: Path = Path("data")


class CrawlConfig(BaseModel):
    user_agent: str
    seed_urls: list[str]
    allowed_domains: list[str]
    max_pages: int = 100
    timeout_seconds: int = 20
    include_pdf_links: bool = False


class ProcessingConfig(BaseModel):
    min_text_length: int = 60
    max_repeated_line_ratio: float = 0.35
    drop_patterns: list[str] = Field(default_factory=list)
    chunk_size: int = 500
    chunk_overlap: int = 100


class EmbeddingConfig(BaseModel):
    model_name: str
    local_path: str = ""
    batch_size: int = 16
    device: str = ""
    dtype: str = ""


class RetrievalConfig(BaseModel):
    mode: Literal["simple", "self_rag", "single_pass"] = "single_pass"
    similarity_top_k: int = 8
    sparse_top_k: int = 8
    sparse_enabled: bool = True
    rerank_top_n: int = 4
    max_rounds: int = 2
    reranker_model: str
    reranker_local_path: str = ""
    reranker_device: str = ""
    reranker_dtype: str = ""


class VectorStoreConfig(BaseModel):
    persist_dir: Path
    collection_name: str


class LLMSharedConfig(BaseModel):
    temperature: float = 0.2
    max_tokens: int = 512
    max_concurrent_requests: int = 1
    stop: list[str] = Field(default_factory=list)
    server_port: int = 8081


class LlamaCppConfig(LLMSharedConfig):

    backend: Literal["llama_cpp"] = "llama_cpp"
    model_path: str = ""
    device_mode: str = "cpu"
    device_name: str = ""
    gpu_layers: int | None = None  # None = 不传 -ngl，由 llama-server 决定
    threads: int | None = None     # None = 不传 -t，用 llama-server 默认 (-1 = auto)
    threads_batch: int | None = None  # None = 不传 -tb
    enable_thinking: bool = False
    reasoning_parser: str = ""     # 空字符串 = 不启用；"qwen3" / "deepseek-r1" 等 = 启用对应 parser
    n_ctx: int = 8192
    # ----- sampling params -----
    top_p: float = 0.95
    top_k: int = 0
    repeat_penalty: float = 1.1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # ----- server / memory params -----
    flash_attn: str = "auto"  # "on" / "off" / "auto"; 始终显式传给 --flash-attn
    ubatch_size: int = 512
    cache_type_k: str | None = "q8_0"  # None = 不传，用 llama-server 默认 (f16)
    cache_type_v: str | None = "q8_0"  # None = 不传，用 llama-server 默认 (f16)
    kv_offload: bool = True  # True = --kv-offload, False = --no-kv-offload
    n_batch: int = 512
    # ----- structured output -----
    structured_output_mode: Literal["json_schema", "gbnf_grammar", "prompt_only"] = "json_schema"

    extra_args: list[str] = Field(default_factory=list)


class VLLMConfig(LLMSharedConfig):

    backend: Literal["vllm"] = "vllm"
    local_path: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    served_model_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    dtype: str = "auto"
    gpu_memory_utilization: float = 0.92
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    data_parallel_size: int = 1
    distributed_executor_backend: str = ""
    max_model_len: int | None = None
    max_num_seqs: int | None = None
    max_num_batched_tokens: int | None = None
    reasoning_parser: str = ""
    api_key: str = ""
    generation_config: str = "vllm"
    trust_remote_code: bool = False
    enable_prefix_caching: bool = True
    enable_chunked_prefill: bool = False
    kv_cache_dtype: str = ""            # "" = auto; "fp8" on Ada/Hopper
    num_scheduler_steps: int | None = None
    swap_space: int | None = None       # CPU swap in GB
    enable_log_requests: bool = False
    disable_uvicorn_access_log: bool = True
    max_parallel_loading_workers: int = 0
    extra_args: list[str] = Field(default_factory=list)


LLMConfig = Annotated[LlamaCppConfig | VLLMConfig, Field(discriminator="backend")]


class AppConfig(BaseModel):
    project: ProjectConfig
    crawl: CrawlConfig
    processing: ProcessingConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    vector_store: VectorStoreConfig
    llm: LLMConfig
