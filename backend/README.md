# SUSTech Campus RAG Backend

Python 后端负责完整 RAG 链路：网页抓取、文本清洗、分块、向量索引、检索、重排序、FastAPI SSE 服务，以及 `llama.cpp` / `vLLM` 两种生成后端。

## 技术栈

- Python `>=3.11,<3.12`
- `uv` 依赖管理
- `httpx + BeautifulSoup + readability-lxml` 网页抓取与正文抽取
- `LlamaIndex + ChromaDB` 向量索引
- `BAAI/bge-small-zh-v1.5` embedding
- `BAAI/bge-reranker-v2-m3` reranker
- `llama.cpp llama-server + Qwen3 GGUF` 本地生成
- `vLLM OpenAI-compatible server` Linux 多卡服务
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

Linux 服务器如果要启用 `vLLM`，现在默认会随着 `uv sync` 一起安装：

```bash
uv sync
```

这里的 `vllm` 依赖已经写在 `pyproject.toml` 里，但只会在 `sys_platform == "linux"` 时安装；macOS 和 Windows 不会安装它。

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
uv run sustech-rag serve --host 127.0.0.1 --port 8001
```

也可以显式指定配置：

```bash
uv run sustech-rag serve --host 127.0.0.1 --port 8001 --config configs/vllm.linux.yaml
```

4 张 `RTX 4090` 的 `vLLM` 样例配置见 [configs/vllm.linux.example.yaml](configs/vllm.linux.example.yaml)。这份样例里，检索侧已经改成 `Qwen/Qwen3-Embedding-4B` 和 `Qwen/Qwen3-Reranker-4B`；本地默认配置 `configs/default.yaml` 仍然保持 BGE 组合。

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
- `llm.backend`：`llama_cpp` 或 `vllm`

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

## llama.cpp / vLLM

后端会根据 `llm.backend` 选择生成服务：

- 非流式 CLI 查询走 `/v1/completions`
- WebUI 流式问答走 `/v1/chat/completions`

`llama.cpp` 后端只从系统 PATH 查找 `llama-server`。保守调试可设置：

```bash
uv run sustech-rag download-llama
uv run sustech-rag download-model
```

这两个命令会分别安装当前平台匹配的 llama.cpp release、下载
embedding/reranker/GGUF。若安装目录不在 PATH 中，llama.cpp 安装命令会打印需要添加的
PATH 命令。后端运行时不会自动下载 GGUF；缺失时请先运行模型下载命令，或把
`llm.model_path` 指向已有 GGUF 文件。

`vLLM` 后端会优先从当前环境的 PATH 查找 `vllm` CLI，因此在 Linux 服务器上通常直接 `uv sync && uv run sustech-rag serve` 就够了。若你确实想复用另一个环境中的 `vllm`，也仍然可以通过 `llm.binary_path` 手动指定。推荐在 Linux/CUDA 环境中使用单机多卡张量并行；4 卡样例已在 `configs/vllm.linux.example.yaml` 给出。

如果你希望 backend 和 vLLM 在同一台 Linux 机器、并且直接共用当前环境，可以这样配置：

```yaml
llm:
  backend: "vllm"
  binary_path: ""
  model_name: "Qwen/Qwen3.6-35B-A3B-FP8"
  tensor_parallel_size: 4
```

如果你后面仍然想把 `vllm` 放回另一个环境，也可以把 `binary_path` 改成对应环境里的 `bin/vllm`。

这样启动命令仍然只有一个：

```bash
uv run sustech-rag serve --config /absolute/path/to/config.yaml
```

如果目标机器是 `4*4090`，我当前更推荐先从官方 `FP8` checkpoint 起步，也就是
`Qwen/Qwen3.6-35B-A3B-FP8`。这样显存余量会更舒服，给 KV cache 和更稳的服务参数留空间。
如果你后续实测在 consumer Ada 环境上更偏好非 `FP8` 权重，再回退到
`Qwen/Qwen3.6-35B-A3B` 也很自然，其他参数基本不用大改。

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
- [../docs/vllm-linux-deploy.md](../docs/vllm-linux-deploy.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
