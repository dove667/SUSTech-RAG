from __future__ import annotations

from pathlib import Path

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
    include_pdf_links: bool = True


class ProcessingConfig(BaseModel):
    min_text_length: int = 80
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
    rerank_top_n: int = 4
    reranker_model: str
    reranker_local_path: str = ""


class VectorStoreConfig(BaseModel):
    persist_dir: Path
    collection_name: str


class LocalLLMConfig(BaseModel):
    binary_path: str = ""
    model_path: str = ""
    n_ctx: int = 8192
    temperature: float = 0.2
    max_tokens: int = 512


class DashScopeLLMConfig(BaseModel):
    model: str = "qwen-plus"
    temperature: float = 0.2


class LLMConfig(BaseModel):
    backend: str = "llama_cpp"
    local: LocalLLMConfig
    dashscope: DashScopeLLMConfig


class AppConfig(BaseModel):
    project: ProjectConfig
    crawl: CrawlConfig
    processing: ProcessingConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    vector_store: VectorStoreConfig
    llm: LLMConfig
