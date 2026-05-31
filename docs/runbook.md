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

`llama-server` 必须在系统 PATH 中。可通过准备脚本下载模型并安装当前平台匹配的
llama.cpp release：

```bash
uv run sustech-rag download-llama
uv run sustech-rag download-model
```

如果 llama.cpp 安装命令提示安装目录不在 PATH 中，按输出添加 PATH 后再启动后端。
运行时不会自动下载 GGUF；缺失时请先运行模型下载命令，或把 `llm.model_path`
指向已有 GGUF 文件。

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

如果要在 Linux 服务器上使用 `vLLM` 多卡部署，并让 backend 去拉起另一个虚拟环境中的
`vllm`，可以直接参考 [vLLM Linux 部署](vllm-linux-deploy.md)。

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

`llama-server binary not found`：安装 llama.cpp，并让 `llama-server` 出现在 PATH。

`GGUF model not found`：把 GGUF 放到 `llm.model_path`，或先运行 `uv run sustech-rag download-model`。

`components not ready`：先确认 Chroma collection 已通过 `index` 构建，再确认 reranker 和 GGUF 路径存在。

前端跨域失败：把前端 origin 加到 `SUSTECH_RAG_CORS_ORIGINS`，多个 origin 用逗号分隔。
