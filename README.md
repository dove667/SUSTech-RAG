# SUSTech Campus RAG

面向南方科技大学公开网页的本地优先 RAG 项目。仓库由两部分组成：

- `backend/`：Python 数据管线与 FastAPI 服务，负责抓取、清洗、分块、向量索引、检索、重排序和 llama.cpp 生成。
- `frontend/`：Vue 3 + Vite WebUI，负责桌面/移动/嵌入/悬浮入口、流式 SSE 对话、主题配置和本地会话存储。

当前默认数据源是 `https://www.sustech.edu.cn/`，默认模型组合是 BGE embedding、BGE reranker 和 Qwen3 GGUF。

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
  -> llama.cpp 流式生成回答
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
- [项目导览](docs/project-guide.md)
- [前后端 API](docs/API.md)

## 当前注意事项

- 后端目前只实现本地 llama.cpp 后端。
- API 请求体里的 `model`、`knowledge_base_ids` 和部分 `options` 已在 schema 中保留，但当前服务端主要使用 YAML 配置。
- 前端会把会话和设置存储在浏览器 `localStorage`。
- 生产部署建议通过反向代理补充鉴权、HTTPS、CORS 白名单和日志采集。
