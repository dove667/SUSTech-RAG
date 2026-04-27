from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """
    定义项目级基础配置，用于描述项目名称和数据目录。
    输入参数：
    - name：项目名称。
    - data_dir：数据目录路径，默认值为 data。
    输出参数：
    - ProjectConfig：返回项目基础配置模型实例。
    """

    name: str
    data_dir: Path = Path("data")


class CrawlConfig(BaseModel):
    """
    定义网页抓取相关配置，用于控制爬虫行为。
    输入参数：
    - user_agent：请求头中的 User-Agent。
    - seed_urls：抓取起始 URL 列表。
    - allowed_domains：允许抓取的域名列表。
    - max_pages：最大抓取页面数。
    - timeout_seconds：单次请求超时时间（秒）。
    - include_pdf_links：是否包含 PDF 链接，默认关闭。
    输出参数：
    - CrawlConfig：返回网页抓取配置模型实例。
    """

    user_agent: str
    seed_urls: list[str]
    allowed_domains: list[str]
    max_pages: int = 100
    timeout_seconds: int = 20
    # PDF 抓取逻辑作为可选开发项保留，当前项目默认关闭。
    include_pdf_links: bool = False


class ProcessingConfig(BaseModel):
    """
    定义文本清洗与分块处理相关配置。
    输入参数：
    - min_text_length：文本保留的最小长度。
    - max_repeated_line_ratio：重复行比例上限。
    - drop_patterns：需要剔除的文本模式列表。
    - chunk_size：切分后的块大小。
    - chunk_overlap：相邻文本块重叠长度。
    输出参数：
    - ProcessingConfig：返回文本处理配置模型实例。
    """

    min_text_length: int = 60
    max_repeated_line_ratio: float = 0.35
    drop_patterns: list[str] = Field(default_factory=list)
    chunk_size: int = 500
    chunk_overlap: int = 100


class EmbeddingConfig(BaseModel):
    """
    定义向量嵌入模型相关配置。
    输入参数：
    - model_name：嵌入模型名称。
    - local_path：本地模型路径，默认为空。
    - batch_size：批量推理大小。
    输出参数：
    - EmbeddingConfig：返回嵌入配置模型实例。
    """

    model_name: str
    local_path: str = ""
    batch_size: int = 16


class RetrievalConfig(BaseModel):
    """
    定义检索与重排序相关配置。
    输入参数：
    - similarity_top_k：相似度召回的候选数量。
    - rerank_top_n：重排序后保留的数量。
    - reranker_model：重排序模型名称。
    - reranker_local_path：本地重排序模型路径，默认为空。
    输出参数：
    - RetrievalConfig：返回检索配置模型实例。
    """

    similarity_top_k: int = 8
    rerank_top_n: int = 4
    reranker_model: str
    reranker_local_path: str = ""


class VectorStoreConfig(BaseModel):
    """
    定义向量数据库持久化相关配置。
    输入参数：
    - persist_dir：向量库持久化目录。
    - collection_name：集合名称。
    输出参数：
    - VectorStoreConfig：返回向量库配置模型实例。
    """

    persist_dir: Path
    collection_name: str


class LocalLLMConfig(BaseModel):
    """
    定义本地 llama.cpp 后端运行参数。
    输入参数：
    - binary_path：llama-cli 可执行文件路径，默认为空。
    - model_path：GGUF 模型路径，默认为空。
    - device_mode：设备模式，默认 cpu。
    - device_name：自定义设备名称，默认为空。
    - gpu_layers：GPU 层数参数，默认 0。
    - threads：推理线程数。
    - threads_batch：批处理线程数。
    - single_turn：是否单轮输出。
    - simple_io：是否使用简化 I/O。
    - reasoning：推理模式开关。
    - n_ctx：上下文长度。
    - temperature：采样温度。
    - max_tokens：最大输出 token 数。
    - extra_args：额外命令行参数列表。
    输出参数：
    - LocalLLMConfig：返回本地大模型配置模型实例。
    """

    binary_path: str = ""
    model_path: str = ""
    device_mode: str = "cpu"
    device_name: str = ""
    gpu_layers: str = "0"
    threads: int = 0
    threads_batch: int = 0
    single_turn: bool = True
    simple_io: bool = True
    reasoning: str = "off"
    n_ctx: int = 8192
    temperature: float = 0.2
    max_tokens: int = 512
    extra_args: list[str] = Field(default_factory=list)


class DashScopeLLMConfig(BaseModel):
    """
    定义 DashScope 云端大模型调用参数。
    输入参数：
    - model：DashScope 模型名称。
    - temperature：采样温度。
    输出参数：
    - DashScopeLLMConfig：返回 DashScope 配置模型实例。
    """

    model: str = "qwen-plus"
    temperature: float = 0.2


class LLMConfig(BaseModel):
    """
    聚合本地与云端大模型后端配置。
    输入参数：
    - backend：当前启用的后端类型。
    - local：本地大模型配置。
    - dashscope：DashScope 大模型配置。
    输出参数：
    - LLMConfig：返回大模型总配置模型实例。
    """

    backend: str = "llama_cpp"
    local: LocalLLMConfig
    dashscope: DashScopeLLMConfig


class AppConfig(BaseModel):
    """
    定义应用全局配置，汇总各模块子配置。
    输入参数：
    - project：项目配置。
    - crawl：抓取配置。
    - processing：文本处理配置。
    - embedding：嵌入配置。
    - retrieval：检索配置。
    - vector_store：向量库配置。
    - llm：大模型配置。
    输出参数：
    - AppConfig：返回应用全局配置模型实例。
    """

    project: ProjectConfig
    crawl: CrawlConfig
    processing: ProcessingConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    vector_store: VectorStoreConfig
    llm: LLMConfig
