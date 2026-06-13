# Backend Architecture

后端围绕一个本地优先的 RAG 流水线组织，CLI 和 API 共用同一套配置、索引、检索和生成组件。

## 数据流

### 单体模式

```text
SiteCrawler
  -> RawDocument
  -> cleaning.build_effective_text
  -> chunk_document
  -> VectorStoreIndex + ChromaDB
  -> RetrievalEngine
  -> BGECrossEncoderReranker
  -> RagService
  -> LlamaCppBackend
  -> FastAPI SSE
```

### 分布式模式（Relay-Worker）

```text
客户端
  -> Relay (SSE)         # 公有云，无模型，仅路由
  -> WebSocket bridge    # Relay ↔ Worker 的 WS 信道
  -> Worker              # GPU 机器，加载全部模型
     -> RagService
     -> RetrievalEngine + Reranker
     -> LlamaCppBackend
  -> WS event 回传
  -> Relay SSE 转发
  -> 客户端
```

## 模块职责

- `config/`：Pydantic 配置模型和 YAML 加载，相对路径解析为绝对路径。
- `crawlers/`：BFS 抓取网页，保存 HTML/PDF 原始文件和 `raw_documents.jsonl`。
- `processing/`：正文重建、噪声过滤、质量检查、分块和 PDF 文本提取。
- `indexing/`：读取 `chunks.jsonl`，写入 ChromaDB collection。
- `retrieval/`：加载 Chroma index，先相似度召回，再 BGE cross-encoder rerank。
- `llm/`：管理持久化 `llama-server` 子进程，并调用 completions/chat-completions。
- `pipeline/`：面向 CLI/API 的编排层。
- `api/`：FastAPI app、路由、schema 和 SSE 帧。
- `relay/`：无模型 FastAPI 中继服务（公有云），管理 Worker WebSocket 连接池和 SSE↔WS 桥接。
- `worker/`：WS 客户端（GPU 机器），连接 Relay 接收任务，封装 `RagService` 执行推理。
- `utils/`：I/O、平台差异、Chroma client、模型缓存和依赖确保。

## API 生命周期

`create_app()` 的 lifespan 会：

1. 加载配置。
2. 初始化 `RagService`，这会加载 embedding、Chroma、reranker 和 LLM backend。
3. 执行 health check。
4. 启动 `llama-server` 并做一次 warm-up。
5. 服务关闭时终止 llama.cpp 子进程。

因此首次启动可能较慢；这属于预加载模型的预期行为。

## 存储约定

```text
data/raw/pages/              原始 HTML 文件
data/raw/pdfs/               PDF 文件，默认未启用抓取
data/raw/raw_documents.jsonl 抓取清单
data/interim/documents.cleaned.jsonl
data/interim/chunks.jsonl
data/vector_store/chroma/    ChromaDB
data/models/                 本地模型
data/models/.cache/          HF_HOME / hub / transformers cache
```

## 当前边界

- 只实现了本地 llama.cpp 后端。
- API schema 已保留 `model` 和 `options`，但大部分运行参数仍由 YAML 配置控制。
- API 鉴权应由反向代理或后续中间件补齐。
- PDF 抓取/解析代码保留，但默认关闭。
