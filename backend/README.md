# SUSTech Campus RAG Backend

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=plastic&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/dove667/SUSTech-RAG)

Python 后端负责完整 RAG 链路：网页抓取、文本清洗、分块、向量索引、检索、重排序、FastAPI SSE 服务和本地 llama.cpp 生成。

## 技术栈

- Python `>=3.11,<3.12`
- `uv` 依赖管理
- `httpx + BeautifulSoup + readability-lxml` 网页抓取与正文抽取
- `LlamaIndex + ChromaDB` 向量索引
- `BAAI/bge-small-zh-v1.5` embedding
- `BAAI/bge-reranker-v2-m3` reranker
- `llama.cpp llama-server + Qwen3 GGUF` 本地生成
- `FastAPI + StreamingResponse` 对外提供 HTTP/SSE API

## 安装

```bash
cd backend
uv sync
```

开发依赖：

```bash
uv sync --extra dev
```

## 数据管线

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

重建 Chroma collection：

```bash
uv run sustech-rag index --rebuild
```

命令会读 `configs/default.yaml`。如果要使用其他配置：

```bash
uv run sustech-rag crawl --config /absolute/path/to/config.yaml
```

## 查询与服务

命令行查询：

```bash
uv run sustech-rag query "南科大本科招生有什么特色？"
```

`query` 会临时启动 `llama-server`、生成一次回答后关闭服务，适合检查索引、检索、reranker 和 LLM 是否能端到端跑通。连续对话建议使用 `serve`，让模型常驻内存。

启动 API 服务：

```bash
uv run sustech-rag serve --host 127.0.0.1 --port 8000
```

也可以显式指定配置：

```bash
uv run sustech-rag serve --host 127.0.0.1 --port 8000 --config /absolute/path/to/config.yaml
```

主要接口：

- `GET /api/health`
- `POST /api/identity`
- `POST /api/chat/completions`
- `POST /api/chat/cancel`

详细协议见 [../docs/API.md](../docs/API.md)。

## 配置

默认配置在 [configs/default.yaml](configs/default.yaml)。最常改的字段：

- `crawl.seed_urls`：起始页面
- `crawl.allowed_domains`：允许抓取的域名
- `crawl.max_pages`：最大抓取页数
- `processing.chunk_size` / `chunk_overlap`：分块大小
- `embedding.local_path`：embedding 本地模型
- `retrieval.reranker_local_path`：reranker 本地模型
- `vector_store.persist_dir`：Chroma 持久化目录
- `llm.model_path`：GGUF 权重
- `llm.server_port`：llama-server 端口

相对路径会按配置文件所在项目根目录解析。

## 数据目录

```text
data/raw/pages/                  原始 HTML
data/raw/raw_documents.jsonl     抓取清单
data/interim/documents.cleaned.jsonl
data/interim/chunks.jsonl
data/vector_store/chroma/        ChromaDB
data/models/                     本地 embedding / reranker / GGUF
data/models/.cache/              Hugging Face 缓存
```

这些目录默认不提交到 Git。

## llama.cpp

后端只使用 `llama-server` 的 OpenAI-compatible 接口，不再调用 `llama-cli`：

- 非流式 CLI 查询走 `/v1/completions`
- WebUI 流式问答走 `/v1/chat/completions`

后端只从系统 PATH 查找 `llama-server`。保守调试可设置：

```bash
uv run sustech-rag download-llama
uv run sustech-rag download-model
```

这两个命令会分别安装当前平台匹配的 llama.cpp release、下载
embedding/reranker/GGUF。若安装目录不在 PATH 中，llama.cpp 安装命令会打印需要添加的
PATH 命令。后端运行时不会自动下载 GGUF；缺失时请先运行模型下载命令，或把
`llm.model_path` 指向已有 GGUF 文件。

```yaml
llm:
  device_mode: "cpu"
  gpu_layers: "0"
```

尝试 GPU/Metal：

```yaml
llm:
  device_mode: "auto"
  gpu_layers: "auto"
```

## 测试与质量检查

```bash
uv run pytest
uv run ruff check .
```

当前测试会加载本地 embedding 缓存；如果模型不存在，部分索引测试会跳过。若 Chroma 客户端 settings 不一致，索引测试可能触发 `An instance of Chroma already exists ... with different settings`。

## 更多文档

- [../docs/project-guide.md](../docs/project-guide.md)
- [../docs/architecture.md](../docs/architecture.md)
- [../docs/runbook.md](../docs/runbook.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
