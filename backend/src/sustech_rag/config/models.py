from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


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


class RetrievalConfig(BaseModel):
    similarity_top_k: int = 8
    sparse_top_k: int = 8
    sparse_enabled: bool = True
    rerank_top_n: int = 4
    reranker_model: str
    reranker_local_path: str = ""


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
    gpu_layers: str = "0"
    threads: int = 0
    threads_batch: int = 0
    reasoning: str = "off"
    n_ctx: int = 8192
    extra_args: list[str] = Field(default_factory=list)


class VLLMConfig(LLMSharedConfig):

    backend: Literal["vllm"] = "vllm"
    model_name: str = ""
    local_path: str = ""
    binary_path: str = ""
    served_model_name: str = ""
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
