# SUSTech Campus RAG

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=plastic&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/dove667/SUSTech-RAG)

面向南方科技大学公开网页的本地优先 RAG 项目。仓库由两部分组成：

- `backend/`：Python 数据管线与 FastAPI 服务，负责抓取、清洗、分块、向量索引、检索、重排序和 llama.cpp 生成。
- `frontend/`：Vue 3 + Vite WebUI，负责桌面/移动/嵌入/悬浮入口、流式 SSE 对话、主题配置和本地会话存储。

当前默认数据源是 `https://www.sustech.edu.cn/`，默认模型组合是 BGE embedding、BGE reranker 和 Qwen3 GGUF。后端现在同时支持 `llama.cpp` 和 `vLLM`，通过 YAML 中的 `llm.backend` 切换；`vLLM` 还可以通过配置指向另一个 conda 环境里的 `bin/vllm`，例如 `~/miniconda3/envs/vllm-0.21/bin/vllm`。面向 Linux 多卡服务器的样例配置已经切到 `Qwen/Qwen3-Embedding-4B` 和 `Qwen/Qwen3-Reranker-4B`。

## 快速启动

后端：

```bash
cd backend
uv sync
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag serve --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认是：

- 后端 API：`http://127.0.0.1:8000/api`
- 前端页面：`http://127.0.0.1:3000`
- Vite 代理：前端的 `/api` 会转发到后端 `127.0.0.1:8000`

## 主要工作流

```text
公开网页
  -> crawl 保存 raw_documents.jsonl 和原始 HTML
  -> preprocess 清洗并过滤 documents.cleaned.jsonl
  -> chunk 生成 chunks.jsonl
  -> index 写入 ChromaDB
  -> retrieve + rerank
  -> llama.cpp / vLLM 流式生成回答
```

常用命令：

```bash
cd backend
uv run sustech-rag paths
uv run sustech-rag query "南科大本科招生有什么特色？"
uv run sustech-rag index --rebuild
```

`query` 会临时启动一次 `llama-server` 并在回答后关闭，适合作为端到端冒烟测试；日常聊天建议使用 `serve` 加前端 WebUI，避免每次提问都重新加载模型。

## 目录说明

```text
backend/configs/default.yaml       后端默认配置
backend/src/sustech_rag/           后端 Python 包
docs/                              API、架构、运行和维护文档
frontend/src/                      前端 Vue 应用
docs/API.md                        当前前后端接口说明
backend/data/                      后端数据、模型、索引目录，不提交 Git
entrypoint.sh                      前端启动脚本，只负责进入 frontend 并运行 Vite
```

`entrypoint.sh` 是前端入口脚本：`bash entrypoint.sh` 会运行 `frontend` 的开发服务器，`bash entrypoint.sh production` 会构建并预览前端。它不会启动后端，也不会构建 RAG 知识库。

## 模型与数据

默认模型位置：

```text
backend/data/models/embeddings/BAAI/bge-small-zh-v1.5
backend/data/models/rerankers/BAAI/bge-reranker-v2-m3
backend/data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf
```

`llama-server` 如果不在系统 PATH 中，后端会尝试自动下载 llama.cpp release。GGUF 权重缺失时，若配置了 `hf_repo_id` 和 `hf_filename`，后端会尝试从 Hugging Face 下载。

## 文档入口

- [后端 README](backend/README.md)
- [前端 README](frontend/README.md)
- [后端架构](docs/architecture.md)
- [运行手册](docs/runbook.md)
- [vLLM Linux 部署](docs/vllm-linux-deploy.md)
- [项目导览](docs/project-guide.md)
- [前后端 API](docs/API.md)

## 当前注意事项

- 后端支持 `llama.cpp` 与 `vLLM` 两种 LLM 后端；Linux 多卡部署可参考 `backend/configs/vllm.linux.example.yaml`。
- API 请求体里的 `model`、`knowledge_base_ids` 和部分 `options` 已在 schema 中保留，但当前服务端主要使用 YAML 配置。
- 前端会把会话和设置存储在浏览器 `localStorage`。
- 生产部署建议通过反向代理补充鉴权、HTTPS、CORS 白名单和日志采集。
