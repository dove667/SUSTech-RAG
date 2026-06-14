# SUSTech Campus RAG

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=plastic&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/dove667/SUSTech-RAG)

面向南方科技大学公开网页的本地优先 RAG 项目。支持两种推理后端：本地 llama.cpp（macOS / Windows / 无 GPU 服务器）和集群 vLLM（Linux 多卡服务器），通过 `--config` 切换。

## 仓库结构

```
backend/          Python RAG 管线 + FastAPI 服务
backend/docs/     后端开发文档
frontend/         Vue 3 + Vite WebUI
docs/             操作、架构、API 文档
deploy/           云端 Relay 启动脚本 + 本地 Worker 环境安装脚本
```

## 快速启动

```bash
# 后端
cd backend
uv sync
uv run sustech-rag download-llama   # llama.cpp 后端：安装 llama-server
uv run sustech-rag download-model   # llama.cpp 后端：下载 embedding / reranker / GGUF
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag serve

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

vLLM 后端在各命令后加 `--config configs/vllm.linux.yaml`，详见 [docs/VLLM-LINUX-DEPLOY.md](docs/VLLM-LINUX-DEPLOY.md)。

## 文档

| 文档 | 内容 |
|---|---|
| [backend/README.md](backend/README.md) | 技术栈、安装、配置字段、数据目录 |
| [deploy/README.md](deploy/README.md) | 部署脚本说明：Relay 入口、Worker 环境安装 |
| [backend/docs/BACKEND-DEV-GUIDE.md](backend/docs/BACKEND-DEV-GUIDE.md) | 代码导览、数据结构、开发约定 |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | 完整操作手册：环境 → 建库 → 启动 → 故障排查 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 数据流、模块职责、API 生命周期 |
| [docs/API.md](docs/API.md) | 前后端接口契约 |
| [docs/VLLM-LINUX-DEPLOY.md](docs/VLLM-LINUX-DEPLOY.md) | Linux 多卡 vLLM 部署指南 |
