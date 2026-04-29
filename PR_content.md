现在有两个PR, 由于出现了冲突, 因此需要你和现有项目比较, 将PR的修改应用到当前项目中(这两个PR修改的内容都已经过评估认为可以)

以下是移除 DashScope 的无效支持的PR diff 内容, 由于是复制的也会会有一些符号不正确



dove667
dove667
committed
2 days ago
commit
37ee687
‎backend/configs/default.yaml‎
+1
-4
Lines changed: 1 addition & 4 deletions
Original file line number	Diff line number	Diff line change
    gpu_layers: "0"
    threads: 0
    threads_batch: 0
    single_turn: true
    single_turn: false
    simple_io: true
    reasoning: "off"
    n_ctx: 8192
    temperature: 0.2
    max_tokens: 512
    extra_args: []
  dashscope:
    model: "qwen-plus"
    temperature: 0.2
‎backend/docs/project-guide.md‎
+1
-1
Lines changed: 1 addition & 1 deletion


Original file line number	Diff line number	Diff line change
负责相似度召回和 `BGE-Reranker-v2-M3` 重排序。

`src/sustech_rag/llm/`
负责本地 `llama.cpp` 与 `DashScope` 的统一调用接口。
负责本地 `llama.cpp` 的统一调用接口。

`src/sustech_rag/utils/`
负责 I/O、平台差异、模型缓存目录等基础工具。
‎backend/docs/runbook.md‎
-1
Lines changed: 0 additions & 1 deletion


Original file line number	Diff line number	Diff line change

需要时填写：

- `DASHSCOPE_API_KEY`
- `LLAMA_CPP_BINARY`
- `LLAMA_CPP_MODEL_PATH`

‎backend/src/sustech_rag/config/models.py‎
+1
-17
Lines changed: 1 addition & 17 deletions
Original file line number	Diff line number	Diff line change
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
    聚合大模型后端配置。
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
‎backend/src/sustech_rag/llm/__init__.py‎
+1
-1
Lines changed: 1 addition & 1 deletion
Original file line number	Diff line number	Diff line change
"""LLM backends."""
‎backend/src/sustech_rag/llm/backends.py‎
+2
-63
Lines changed: 2 additions & 63 deletions
Original file line number	Diff line number	Diff line change

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import dashscope
from sustech_rag.config.models import AppConfig
from sustech_rag.utils.platform import default_llama_binary_name, is_windows


class LLMBackend(ABC):
    """
    LLM 后端抽象基类。
    定义所有大语言模型后端的统一接口。
    输入参数：无。
    输出参数：用于实现统一生成能力的后端抽象对象。
    """
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        生成文本结果。
        接收提示词并返回模型生成内容的统一接口。
        输入参数：prompt，用户输入的提示词文本。
        输出参数：模型生成的文本结果。
        """
        raise NotImplementedError
class LlamaCppBackend(LLMBackend):
class LlamaCppBackend:
    def __init__(self, config: AppConfig) -> None:
        """
        初始化 llama.cpp 后端。
            return self.device_name
        if mode in {"metal", "gpu"}:
            return self.device_name or None
        return self.device_name or mode
class DashScopeBackend(LLMBackend):
    def __init__(self, config: AppConfig) -> None:
        """
        初始化 DashScope 后端。
        读取 DashScope 模型配置并设置 API 密钥。
        输入参数：config，应用配置对象，包含 DashScope 相关设置。
        输出参数：无，完成实例属性初始化。
        """
        self.model = config.llm.dashscope.model
        self.temperature = config.llm.dashscope.temperature
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")
    def generate(self, prompt: str) -> str:
        """
        调用 DashScope 生成文本。
        通过 DashScope Generation API 发送提示词并返回生成结果。
        输入参数：prompt，用户输入的提示词文本。
        输出参数：DashScope 返回并清理后的文本结果。
        """
        response = dashscope.Generation.call(
            model=self.model,
            prompt=prompt,
            temperature=self.temperature,
        )
        return response.output.text.strip()
def build_llm_backend(config: AppConfig) -> LLMBackend:
    """
    构建 LLM 后端实例。
    根据配置选择并创建 DashScope 或 llama.cpp 后端实现。
    输入参数：config，应用配置对象，包含 LLM 后端类型与参数。
    输出参数：已初始化的 LLMBackend 实例。
    """
    if config.llm.backend == "dashscope":
        return DashScopeBackend(config)
    return LlamaCppBackend(config)
        return self.device_name or mode
‎backend/src/sustech_rag/pipeline/rag_service.py‎
+2
-6
Lines changed: 2 additions & 6 deletions
Original file line number	Diff line number	Diff line change
from __future__ import annotations

from sustech_rag.config.models import AppConfig
from sustech_rag.llm.backends import build_llm_backend
from sustech_rag.llm.backends import LlamaCppBackend
from sustech_rag.retrieval.engine import RetrievalEngine


class RagService:
    """
    封装检索与大模型生成的问答服务。
    输入参数：
        config: 应用配置对象。
    输出参数：
        无。
    """

    def __init__(self, config: AppConfig) -> None:
        """
        self.config = config
        self.retrieval = RetrievalEngine(config)
        self.llm = build_llm_backend(config)
        self.llm = LlamaCppBackend(config)

    def answer(self, query: str) -> str:
        """
‎backend/src/sustech_rag/retrieval/engine.py‎
-2
Lines changed: 0 additions & 2 deletions
Original file line number	Diff line number	Diff line change
class RetrievalEngine:
    """
    初始化向量检索与重排序引擎，并提供查询检索能力。
    输入参数：无。
    输出参数：RetrievalEngine 实例，用于执行召回与 rerank。
    """

    def __init__(self, config: AppConfig) -> None:
‎backend/tests/test_builders.py‎
-2
Lines changed: 0 additions & 2 deletions
Original file line number	Diff line number	Diff line change
from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    DashScopeLLMConfig,
    EmbeddingConfig,
    LLMConfig,
    LocalLLMConfig,
        llm=LLMConfig(
            backend="llama_cpp",
            local=LocalLLMConfig(),
            dashscope=DashScopeLLMConfig(),
        ),
    )

‎backend/tests/test_config.py‎
+4
-4
Lines changed: 4 additions & 4 deletions
Original file line number	Diff line number	Diff line change
    assert config.project.name == "sustech-campus-rag"
    assert config.embedding.model_name == "BAAI/bge-small-zh-v1.5"
    assert config.processing.min_text_length == 60
    assert str(config.embedding.local_path).endswith("data/model/embeddings/BAAI/bge-small-zh-v1.5")
    assert str(config.embedding.local_path).endswith("data/models/embeddings/BAAI/bge-small-zh-v1.5")
    assert str(config.retrieval.reranker_local_path).endswith(
        "data/model/rerankers/BAAI/bge-reranker-v2-m3"
        "data/models/rerankers/BAAI/bge-reranker-v2-m3"
    )
    assert str(config.vector_store.persist_dir).endswith("data/index/chroma")
    assert str(config.llm.local.model_path).endswith("data/model/llm/qwen/Qwen3-8B-Q4_K_M.gguf")
    assert str(config.vector_store.persist_dir).endswith("data/vector_store/chroma")
    assert str(config.llm.local.model_path).endswith("data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf")
‎backend/tests/test_indexing.py‎
-2
Lines changed: 0 additions & 2 deletions
Original file line number	Diff line number	Diff line change
from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    DashScopeLLMConfig,
    EmbeddingConfig,
    LLMConfig,
    LocalLLMConfig,
        ),
        llm=LLMConfig(
            local=LocalLLMConfig(),
            dashscope=DashScopeLLMConfig(),
        ),
    )

‎backend/.env.example‎
-1
Lines changed: 0 additions & 1 deletion
Original file line number	Diff line number	Diff line change
SUSTECH_RAG_CONFIG=configs/default.yaml
DASHSCOPE_API_KEY=
LLAMA_CPP_BINARY=
LLAMA_CPP_MODEL_PATH=
‎backend/.gitignore‎
+3
Lines changed: 3 additions & 0 deletions
Original file line number	Diff line number	Diff line change
# Keep data dir in repo if empty
!data/.gitkeep

# Agent instructions
AGENTS.md
# Logs
*.log

‎backend/pyproject.toml‎
-1
Lines changed: 0 additions & 1 deletion


Original file line number	Diff line number	Diff line change
dependencies = [
  "beautifulsoup4==4.12.3",
  "chromadb==0.5.23",
  "dashscope==1.20.13",
  "httpx==0.28.1",
  "llama-index==0.12.21",
  "llama-index-embeddings-huggingface==0.5.1",
‎backend/README.md‎
+2
-4
Lines changed: 2 additions & 4 deletions


Original file line number	Diff line number	Diff line change

- End-to-end pipeline：从公开网页抓取到本地问答全链路打通
- Local-first：优先使用本地 embedding、reranker、GGUF 模型
- Dual LLM backends：支持 `llama.cpp` 本地推理和 `DashScope API`
- Cross-platform：兼容 macOS / Windows 的路径与执行方式
- Inspectable data flow：每一步都把中间结果落盘，便于调试与复现
- Lightweight stack：`uv + LlamaIndex + ChromaDB`，适合个人开发和教学演示
- Embedding：`BAAI/bge-small-zh-v1.5`
- Reranker：`BAAI/bge-reranker-v2-m3`
- 本地生成：`llama.cpp + Qwen3-8B GGUF`
- 备选生成：阿里百炼 `DashScope API`
- 依赖管理：`uv`
- Python 版本：`3.11`

- Embedding: `BAAI/bge-small-zh-v1.5`
- Reranking: `BAAI/bge-reranker-v2-m3`
- Local inference: `llama.cpp + Qwen3-8B GGUF`
- Optional API inference: `DashScope`
- Local inference: `llama.cpp + Qwen3-8B GGUF`

## 你最需要知道的目录

src/sustech_rag/processing/   清洗、分块、保留的 PDF 解析代码
src/sustech_rag/indexing/     嵌入与向量索引
src/sustech_rag/retrieval/    召回与重排序
src/sustech_rag/llm/          llama.cpp / DashScope 后端
src/sustech_rag/llm/          llama.cpp 后端
data/models/                  本地模型目录
data/raw/                     原始抓取结果
data/interim/                 清洗与分块中间结果
‎backend/uv.lock‎
-15
Lines changed: 0 additions & 15 deletions


Original file line number	Diff line number	Diff line change
    { name = "nvidia-nvtx", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]

[[package]]
name = "dashscope"
version = "1.20.13"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "aiohttp" },
    { name = "requests" },
    { name = "websocket-client" },
]
wheels = [
    { url = "https://files.pythonhosted.org/packages/ed/ea/6d0a41151dfe3a9e92c0d67182e923f2be25893ba6e92d2b3fdfb9dc4554/dashscope-1.20.13-py3-none-any.whl", hash = "sha256:68fb7e9ffa260ebba7188520ca3e462b651ead0d5ee470ccd510c84856be7465", size = 1264298, upload-time = "2024-11-18T07:16:09.472Z" },
]
[[package]]
name = "dataclasses-json"
version = "0.6.7"
dependencies = [
    { name = "beautifulsoup4" },
    { name = "chromadb" },
    { name = "dashscope" },
    { name = "httpx" },
    { name = "llama-index" },
    { name = "llama-index-embeddings-huggingface" },
requires-dist = [
    { name = "beautifulsoup4", specifier = "==4.12.3" },
    { name = "chromadb", specifier = "==0.5.23" },
    { name = "dashscope", specifier = "==1.20.13" },
    { name = "httpx", specifier = "==0.28.1" },
    { name = "llama-index", specifier = "==0.12.21" },
    { name = "llama-index-embeddings-huggingface", specifier = "==0.5.1" },



第二个PR
优化 indexing：
1. 支持重建（--rebuild）或追加
2. 调整之前 data/下的冗余cache 目录和与之对应的环境变量
3. 增加新的 text_indexing.py

Co-authored-by: Copilot <copilot@github.com>
dove667Copilot
dove667
and
Copilot
committed
2 days ago
commit
1b24c8f
‎backend/src/sustech_rag/cli/main.py‎
+6
-2
Lines changed: 6 additions & 2 deletions
Original file line number	Diff line number	Diff line change


@app.command()
def index(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
def index(
    config: str = typer.Option(None, help="Path to YAML config file."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Delete existing collection before building index."),
) -> None:
    """
    构建向量索引，并输出索引持久化目录信息。
    输入参数：
        config：YAML 配置文件路径，用于加载索引相关配置。
        rebuild：是否重建索引，若为 True 则先删除已有 collection。
    输出参数：
        None：无返回值，结果通过终端输出。
    """
    from sustech_rag.indexing.vector_index import build_vector_index

    app_config = load_config(config)
    _ = build_vector_index(app_config)
    _ = build_vector_index(app_config, rebuild=rebuild)
    typer.echo(f"Indexed chunks into {app_config.vector_store.persist_dir}.")


‎backend/src/sustech_rag/indexing/vector_index.py‎
+17
-9
Lines changed: 17 additions & 9 deletions
Original file line number	Diff line number	Diff line change
from sustech_rag.utils.runtime import prepare_model_cache


def build_vector_index(config: AppConfig) -> VectorStoreIndex:
def build_vector_index(config: AppConfig, rebuild: bool = False) -> VectorStoreIndex:
    """
    根据配置读取分块数据、初始化向量模型与 Chroma 向量库，并构建向量索引。
    输入参数：
        config: 应用配置对象，包含数据目录、embedding 配置与向量库配置。
        rebuild: 是否重建索引。若为 True，先删除已有 collection 再重新构建。
    输出参数：
        VectorStoreIndex: 构建完成的 LlamaIndex 向量索引对象。
    """
    prepare_model_cache(config.project.data_dir)
    huggingface_dir = prepare_model_cache(config.project.data_dir)
    model_ref = config.embedding.local_path or config.embedding.model_name
    embed_model = HuggingFaceEmbedding(
        model_name=model_ref,
        cache_folder=str(huggingface_dir),
        embed_batch_size=config.embedding.batch_size,
    )
    chroma_client = chromadb.PersistentClient(path=str(config.vector_store.persist_dir))
    if rebuild:
        try:
            chroma_client.delete_collection(config.vector_store.collection_name)
        except ValueError:
            # Chroma raises when the collection does not exist yet.
            pass
    collection = chroma_client.get_or_create_collection(config.vector_store.collection_name)
    chunks = read_jsonl(config.project.data_dir / "interim" / "chunks.jsonl")
    documents = [
        Document(
        )
        for row in chunks
    ]
    model_ref = config.embedding.local_path or config.embedding.model_name
    embed_model = HuggingFaceEmbedding(
        model_name=model_ref,
        cache_folder=str(config.project.data_dir / "cache" / "huggingface"),
    )
    chroma_client = chromadb.PersistentClient(path=str(config.vector_store.persist_dir))
    collection = chroma_client.get_or_create_collection(config.vector_store.collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(
‎backend/src/sustech_rag/retrieval/engine.py‎
+3
-2
Lines changed: 3 additions & 2 deletions
Original file line number	Diff line number	Diff line change
        输出参数：无。
        """
        self.config = config
        prepare_model_cache(config.project.data_dir)
        huggingface_dir = prepare_model_cache(config.project.data_dir)
        model_ref = config.embedding.local_path or config.embedding.model_name
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=model_ref,
            cache_folder=str(config.project.data_dir / "cache" / "huggingface"),
            cache_folder=str(huggingface_dir),
            embed_batch_size=config.embedding.batch_size,
        )
        client = chromadb.PersistentClient(path=str(config.vector_store.persist_dir))
        collection = client.get_or_create_collection(config.vector_store.collection_name)
‎backend/src/sustech_rag/utils/runtime.py‎
+8
-11
Lines changed: 8 additions & 11 deletions
Original file line number	Diff line number	Diff line change

def prepare_model_cache(base_dir: Path) -> Path:
    """
    初始化模型相关缓存目录并设置常用环境变量。
    输入参数：base_dir，缓存根目录。
    输出参数：HuggingFace 缓存目录 Path 对象。
    初始化模型目录并设置 HuggingFace 运行时环境变量。
    输入参数：base_dir，数据根目录。
    输出参数：HuggingFace 模型目录 Path 对象。
    """
    cache_dir = ensure_dir(base_dir / "cache" / "huggingface")
    os.environ.setdefault("HF_HOME", str(cache_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_dir / "transformers"))
    llama_index_cache = ensure_dir(base_dir / "cache" / "llama_index")
    os.environ.setdefault("XDG_CACHE_HOME", str(base_dir / "cache"))
    os.environ.setdefault("LLAMA_INDEX_CACHE_DIR", str(llama_index_cache))
    return cache_dir
    model_dir = ensure_dir(base_dir / "models" / ".cache")
    os.environ.setdefault("HF_HOME", str(model_dir))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(model_dir / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(model_dir / "transformers"))
    return model_dir
‎backend/tests/test_config.py‎
+6
Lines changed: 6 additions & 0 deletions
Original file line number	Diff line number	Diff line change
    assert config.project.name == "sustech-campus-rag"
    assert config.embedding.model_name == "BAAI/bge-small-zh-v1.5"
    assert config.processing.min_text_length == 60
    assert str(config.embedding.local_path).endswith("data/model/embeddings/BAAI/bge-small-zh-v1.5")
    assert str(config.retrieval.reranker_local_path).endswith(
        "data/model/rerankers/BAAI/bge-reranker-v2-m3"
    )
    assert str(config.vector_store.persist_dir).endswith("data/index/chroma")
    assert str(config.llm.local.model_path).endswith("data/model/llm/qwen/Qwen3-8B-Q4_K_M.gguf")
‎backend/tests/test_indexing.py‎
+143
Lines changed: 143 additions & 0 deletions
Original file line number	Diff line number	Diff line change
from __future__ import annotations
import os
from pathlib import Path
import pytest
from sustech_rag.config.models import (
    AppConfig,
    CrawlConfig,
    DashScopeLLMConfig,
    EmbeddingConfig,
    LLMConfig,
    LocalLLMConfig,
    ProcessingConfig,
    ProjectConfig,
    RetrievalConfig,
    VectorStoreConfig,
)
def _make_config(tmp_path: Path, batch_size: int = 4) -> AppConfig:
    local_embedding_dir = Path("data/models/embeddings/BAAI/bge-small-zh-v1.5")
    local_embedding_path = str(local_embedding_dir) if local_embedding_dir.exists() else ""
    return AppConfig(
        project=ProjectConfig(name="test", data_dir=tmp_path),
        crawl=CrawlConfig(
            user_agent="test-agent",
            seed_urls=["https://example.com"],
            allowed_domains=["example.com"],
        ),
        processing=ProcessingConfig(),
        embedding=EmbeddingConfig(
            model_name="BAAI/bge-small-zh-v1.5",
            local_path=local_embedding_path,
            batch_size=batch_size,
        ),
        retrieval=RetrievalConfig(reranker_model="BAAI/bge-reranker-v2-m3"),
        vector_store=VectorStoreConfig(
            persist_dir=tmp_path / "vector_store",
            collection_name="test-collection",
        ),
        llm=LLMConfig(
            local=LocalLLMConfig(),
            dashscope=DashScopeLLMConfig(),
        ),
    )
class TestIndexing:
    """Indexing integration tests. Requires embedding model to be cached."""
    @pytest.fixture(autouse=True)
    def _check_model(self) -> None:
        if not Path("data/models/embeddings/BAAI/bge-small-zh-v1.5").exists():
            pytest.skip("Embedding model not cached")
        os.environ["HF_HUB_OFFLINE"] = "1"
    def test_index_inserts_all_chunks(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl
        interim = ensure_dir(tmp_path / "interim")
        chunks = [
            {
                "chunk_id": f"chunk-{i}",
                "doc_id": "doc-1",
                "title": "Test",
                "text": f"Chunk text number {i} with some content here.",
                "source_url": "https://example.com/",
            }
            for i in range(10)
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)
        from sustech_rag.indexing.vector_index import build_vector_index
        config = _make_config(tmp_path, batch_size=8)
        build_vector_index(config, rebuild=True)
        import chromadb
        client = chromadb.PersistentClient(path=str(tmp_path / "vector_store"))
        coll = client.get_collection("test-collection")
        assert coll.count() == 10
    def test_rebuild_replaces_collection(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl
        interim = ensure_dir(tmp_path / "interim")
        chunks = [
            {
                "chunk_id": "chunk-0",
                "doc_id": "doc-1",
                "title": "Test",
                "text": "Initial chunk.",
                "source_url": "https://example.com/",
            }
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)
        import chromadb
        config = _make_config(tmp_path)
        chroma_path = str(tmp_path / "vector_store")
        from sustech_rag.indexing.vector_index import build_vector_index
        build_vector_index(config, rebuild=False)
        client = chromadb.PersistentClient(path=chroma_path)
        coll = client.get_collection("test-collection")
        assert coll.count() == 1
        chunks = [
            {
                "chunk_id": "chunk-new",
                "doc_id": "doc-2",
                "title": "New",
                "text": "New chunk after rebuild.",
                "source_url": "https://example.com/new",
            }
        ]
        write_jsonl(interim / "chunks.jsonl", chunks)
        build_vector_index(config, rebuild=True)
        coll = client.get_collection("test-collection")
        assert coll.count() == 1
        results = coll.get()
        assert len(results["documents"]) == 1
        assert results["documents"][0] == "New chunk after rebuild."
    def test_empty_chunks_returns_index(self, tmp_path: Path) -> None:
        from sustech_rag.utils.io import ensure_dir, write_jsonl
        interim = ensure_dir(tmp_path / "interim")
        write_jsonl(interim / "chunks.jsonl", [])
        from sustech_rag.indexing.vector_index import build_vector_index
        config = _make_config(tmp_path)
        index = build_vector_index(config, rebuild=True)
        assert index is not None