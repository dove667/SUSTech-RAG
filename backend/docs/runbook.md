# Backend Runbook

## 1. 准备环境

```bash
cd backend
uv sync
```

如需运行测试和 lint：

```bash
uv sync --extra dev
```

## 2. 检查配置

```bash
uv run sustech-rag paths
```

默认配置文件是 `configs/default.yaml`。重要路径：

- `project.data_dir`
- `vector_store.persist_dir`
- `embedding.local_path`
- `retrieval.reranker_local_path`
- `llm.model_path`

## 3. 准备模型

默认本地模型位置：

```text
data/models/embeddings/BAAI/bge-small-zh-v1.5
data/models/rerankers/BAAI/bge-reranker-v2-m3
data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf
```

如果 `llama-server` 不在 PATH，后端会尝试下载 llama.cpp release。如果 GGUF 不存在，后端会根据 `hf_repo_id` 和 `hf_filename` 尝试下载模型文件。

## 4. 构建知识库

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

需要清空并重建 collection：

```bash
uv run sustech-rag index --rebuild
```

## 5. 本地验证

```bash
uv run sustech-rag query "南科大有哪些学院？"
```

这条命令会临时启动 `llama-server` 并在回答后关闭；如果要连续测试多轮问答，请启动 API 服务。

启动 API：

```bash
uv run sustech-rag serve --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

## 6. 与前端联调

```bash
cd ../frontend
npm install
npm run dev
```

前端默认把 `/api` 代理到 `127.0.0.1:8000`。

## 7. 测试

```bash
uv run pytest
uv run ruff check .
```

索引测试依赖本地 embedding 模型；模型不存在时会跳过。Chroma 0.5.x 会按 path 缓存客户端实例，测试或脚本中混用不同 `Settings` 可能触发 settings 不一致异常。

## 8. 常见故障

`llama-server binary not found`：安装 llama.cpp，或让 `llama-server` 出现在 PATH，或设置 `llm.binary_path`。

`GGUF model not found`：把 GGUF 放到 `llm.model_path`，或配置 `hf_repo_id` / `hf_filename` 允许自动下载。

`components not ready`：先确认 Chroma collection 已通过 `index` 构建，再确认 reranker 和 GGUF 路径存在。

前端跨域失败：把前端 origin 加到 `SUSTECH_RAG_CORS_ORIGINS`，多个 origin 用逗号分隔。
