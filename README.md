# SUSTech Campus RAG

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=plastic&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/dove667/SUSTech-RAG)

面向南方科技大学公开网页的本地优先 RAG 项目。仓库由三部分组成：

- `backend/`：Python 数据管线与 FastAPI 服务，负责抓取、清洗、分块、向量索引、检索、重排序和 llama.cpp 生成。支持分布式部署：Relay（公有云无模型路由）+ Worker（GPU 机器推理）。
- `frontend/`：Vue 3 + Vite WebUI，负责桌面/移动/嵌入/悬浮入口、流式 SSE 对话、主题配置和本地会话存储。
- `install_worker.sh` / `install_worker.ps1`：GPU 机器一键 Worker 安装脚本。

当前默认数据源是 `https://www.sustech.edu.cn/`，默认模型组合是 BGE embedding、BGE reranker 和 Qwen3 GGUF。后端现在同时支持 `llama.cpp` 和 `vLLM`，通过 YAML 中的 `llm.backend` 切换；Linux 上 `uv sync` 会自动安装 `vllm`，而 macOS / Windows 会跳过它。面向 Linux 多卡服务器的样例配置已经切到 `Qwen/Qwen3-Embedding-4B` 和 `Qwen/Qwen3-Reranker-4B`。

## 快速启动

后端：

```bash
cd backend
uv sync
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag serve
```

前端：

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认是：

- 后端 API：`http://127.0.0.1:8001/api`
- 前端页面：`http://127.0.0.1:3000`
- Vite 代理：前端的 `/api` 会转发到后端 `127.0.0.1:8001`

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
uv run sustech-rag paths                                      # 查看数据路径
uv run sustech-rag query "南科大本科招生有什么特色？"             # 端到端冒烟测试
uv run sustech-rag index --rebuild                            # 重建 Chroma 索引
uv run sustech-rag relay --host 0.0.0.0 --port 8080           # 启动 Relay（公有云）
uv run sustech-rag worker --relay ws://<host>:8080/ws/worker  # 启动 Worker（GPU）
```

`query` 会临时启动一次 `llama-server` 并在回答后关闭，适合作为端到端冒烟测试；日常聊天建议使用 `serve` 加前端 WebUI，避免每次提问都重新加载模型。

## 目录说明

```text
backend/                            Python 后端（数据管线 + FastAPI + Relay/Worker）
frontend/                           Vue 3 + Vite WebUI
docs/                               API、架构、运行和维护文档
entrypoint.sh                       生产入口脚本：启动 Relay + TCP 代理（:8080 → :3000）
install_worker.sh                   一键 Worker 安装脚本（Linux/macOS）
install_worker.ps1                  一键 Worker 安装脚本（Windows）
```

`entrypoint.sh` 是应用盒入口脚本：启动 Relay（无模型路由 + 前端静态托管）和一个 :8080 → :3000 的 TCP 代理。**不启动后端 API 服务**——GPU 推理由独立的 Worker 进程提供。

`install_worker.sh` / `install_worker.ps1` 用于在 GPU 机器上一键安装依赖并连接 Relay。

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