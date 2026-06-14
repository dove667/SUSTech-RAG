# Backend Architecture

后端围绕一个本地优先的 RAG 流水线组织，CLI 和 API 共用同一套配置、索引、检索和生成组件。

## 数据流

### 单体模式（llama.cpp 或 vLLM）

```
SiteCrawler
  -> RawDocument
  -> cleaning.build_effective_text
  -> chunk_document
  -> VectorStoreIndex + ChromaDB
  -> RetrievalEngine
  -> BGECrossEncoderReranker / Qwen3Reranker
  -> RagService
  -> LlamaCppBackend 或 VLLMBackend
  -> FastAPI SSE
```

### 分布式模式（Relay-Worker）

```
客户端
  -> Relay (SSE)         # 公有云，无模型，仅路由
  -> WebSocket bridge    # Relay ↔ Worker 的 WS 信道
  -> Worker              # GPU 机器，加载全部模型
     -> RagService
     -> RetrievalEngine + Reranker
     -> LlamaCppBackend 或 VLLMBackend
  -> WS event 回传
  -> Relay SSE 转发
  -> 客户端
```

## 模块职责

- `config/`：Pydantic 配置模型和 YAML 加载，相对路径解析为绝对路径。
- `crawlers/`：BFS 抓取网页，保存 HTML/PDF 原始文件和 `raw_documents.jsonl`。
- `processing/`：正文重建、噪声过滤、质量检查、分块和 PDF 文本提取。
- `indexing/`：读取 `chunks.jsonl`，写入 ChromaDB collection。
- `retrieval/`：加载 Chroma index，先相似度召回，再 cross-encoder rerank。
- `llm/`：统一推理后端接口，支持 llama.cpp（管理 `llama-server` 子进程）和 vLLM（管理 `vllm serve` 子进程）。
- `pipeline/`：面向 CLI/API 的编排层。
- `api/`：FastAPI app、路由、schema 和 SSE 帧。
- `relay/`：无模型 FastAPI 中继服务（公有云），管理 Worker WebSocket 连接池和 SSE↔WS 桥接。
- `worker/`：WS 客户端（GPU 机器），连接 Relay 接收任务，封装 `RagService` 执行推理。
- `utils/`：I/O、平台差异、Chroma client、模型下载。

## API 生命周期

`create_app()` 的 lifespan 会：

1. 加载配置。
2. 初始化 `RagService`，加载 embedding、Chroma、reranker 和 LLM backend。
3. 执行 health check。
4. 启动推理服务子进程（llama-server 或 vllm serve）并做一次 warm-up。
5. 服务关闭时终止子进程。

首次启动较慢是预期行为（模型预加载）。

## 存储约定

```
data/raw/pages/              原始 HTML 文件
data/raw/pdfs/               PDF 文件（默认未启用抓取）
data/raw/raw_documents.jsonl 抓取清单
data/interim/documents.cleaned.jsonl
data/interim/chunks.jsonl
data/vector_store/chroma/    ChromaDB
data/models/                 本地模型（embedding / reranker / GGUF）
data/models/.cache/          HF_HOME / hub / transformers cache
```

## 设计边界

- API schema 已保留 `model` 和 `options`，但运行参数主要由 YAML 配置控制。
- API 鉴权应由反向代理或后续中间件补齐，后端本身不内建。
- PDF 抓取/解析代码保留，但 `crawl.include_pdf_links` 默认关闭。
