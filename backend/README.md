# SUSTech Campus RAG Backend

Python 后端负责完整 RAG 链路：网页抓取、文本清洗、分块、向量索引、检索、重排序、FastAPI SSE 服务，以及 `llama.cpp` / `vLLM` 两种生成后端。

## 技术栈

- Python `>=3.11,<3.12`，`uv` 依赖管理
- `httpx + BeautifulSoup + readability-lxml` 网页抓取与正文抽取
- `LlamaIndex + ChromaDB` 向量索引
- `FastAPI + StreamingResponse` HTTP/SSE API
- llama.cpp 后端：`llama-server` + Qwen3 GGUF，本地单机
- vLLM 后端：`vllm serve` OpenAI-compatible server，Linux 多卡

## 安装

```bash
cd backend
uv sync              # 生产依赖（Linux 同时安装 vllm）
uv sync --extra dev  # 含 pytest、ruff
```

## 配置

默认配置：`configs/default.yaml`（llama.cpp）。vLLM 配置：`configs/vllm.linux.yaml`。

所有 CLI 命令通过 `--config <yaml>` 切换配置，未指定时读取 `default.yaml`。相对路径按配置文件所在目录解析。

常用字段：

| 字段 | 说明 |
|---|---|
| `llm.backend` | `llama_cpp` 或 `vllm` |
| `llm.model_path` | GGUF 路径（llama.cpp） |
| `llm.local_path` | 模型目录（vLLM） |
| `embedding.local_path` | embedding 模型路径 |
| `retrieval.reranker_local_path` | reranker 模型路径 |
| `vector_store.persist_dir` | ChromaDB 持久化目录 |
| `crawl.seed_urls` | 抓取起始页 |
| `crawl.max_pages` | 最大抓取页数 |
| `llm.server_port` | 推理服务内部端口（默认 8081） |

## 数据目录

```
data/raw/pages/                  原始 HTML
data/raw/raw_documents.jsonl     抓取清单
data/interim/documents.cleaned.jsonl
data/interim/chunks.jsonl
data/vector_store/chroma/        ChromaDB
data/models/                     embedding / reranker / GGUF
data/models/.cache/              Hugging Face 缓存
```

以上目录均不提交到 Git。

## 文档

- [docs/BACKEND-DEV-GUIDE.md](docs/BACKEND-DEV-GUIDE.md)：代码导览、数据结构、开发约定
- [../docs/RUNBOOK.md](../docs/RUNBOOK.md)：完整操作手册
- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)：数据流与模块职责
- [../docs/API.md](../docs/API.md)：前后端接口契约
- [../docs/VLLM-LINUX-DEPLOY.md](../docs/VLLM-LINUX-DEPLOY.md)：Linux 多卡 vLLM 部署
