# vLLM Linux 部署

本文针对以下部署环境：

- 3 张 RTX 4090，CUDA driver 较旧（CUDA 11.8 兼容）
- `cuda:0` + `cuda:1`：运行大模型（tensor parallel，2 卡）
- `cuda:2`：运行 embedding 和 reranker
- 配置文件：`backend/configs/vllm.linux.yaml`

## 依赖版本说明

项目 Python 依赖锁定了与旧 CUDA driver 兼容的版本组合：

- `torch==2.7.1`，从 `pytorch-cu118` 源安装（`https://download.pytorch.org/whl/cu118`）
- `vllm==0.10.1`，Linux 平台条件依赖，随 `uv sync` 自动安装

这是经过权衡后的版本组合：更新的版本需要更高版本的 CUDA driver，更旧的版本不支持当前使用的模型。**不要单独升级 torch 或 vllm**，两者需要作为整体一起调整。

## 1. 准备环境

```bash
cd /srv/sustech-rag/backend    # 或你的实际路径
uv sync
```

`uv sync` 会自动创建 `.venv`，从 `pytorch-cu118` 源安装 torch，并安装 `vllm==0.10.1`。Linux 上无需单独创建 conda 环境。

确认 vllm 可用：

```bash
uv run vllm --help
```

## 2. 配置文件

使用 `configs/vllm.linux.yaml`，关键字段：

```yaml
embedding:
  model_name: "Qwen/Qwen3-Embedding-4B"
  local_path: "/data1/zsh/models/Qwen3-Embedding-4B"
  device: "cuda:2"
  dtype: "bfloat16"

retrieval:
  reranker_model: "Qwen/Qwen3-Reranker-4B"
  reranker_local_path: "/data1/zsh/models/Qwen3-Reranker-4B"
  reranker_device: "cuda:2"
  reranker_dtype: "bfloat16"

llm:
  backend: "vllm"
  local_path: "/data1/zsh/models/Qwen3-30B-A3B-Instruct-2507-AWQ"
  served_model_name: "qwen3-30b-a3b-instruct-2507-awq"
  tensor_parallel_size: 2        # cuda:0 + cuda:1
  distributed_executor_backend: "mp"
  reasoning_parser: "qwen3"
```

将 `local_path` / `reranker_local_path` / `embedding.local_path` 改为实际模型路径。

## 3. 构建知识库

```bash
uv run sustech-rag crawl --config configs/vllm.linux.yaml
uv run sustech-rag preprocess --config configs/vllm.linux.yaml
uv run sustech-rag index --config configs/vllm.linux.yaml
```

已有 `data/` 目录时可直接复用，不必重新抓取。

## 4. 启动服务

```bash
uv run sustech-rag serve --host 0.0.0.0 --port 8001 --config configs/vllm.linux.yaml
```

backend 会读取配置中的 `llm.backend: vllm`，自动拉起当前环境中的 `vllm serve`。首次启动较慢（模型加载 + warm-up）。

健康检查：

```bash
curl http://127.0.0.1:8001/api/health
```

## 5. 常见调整

**吞吐偏低：**
- 调大 `llm.max_num_seqs`
- 调大 `llm.max_concurrent_requests`
- 确认 `tensor_parallel_size: 2` 已生效

**显存吃紧：**
- 先降低 `max_model_len`
- 再降低 `max_num_batched_tokens`
- 最后降低 `max_num_seqs`
- embedding / reranker 固定在 `cuda:2`，不与 LLM 争显存

**找不到 vllm：**
- 确认在 `backend/` 目录下通过 `uv run` 调用，不要直接用系统 `vllm`
- 手动运行 `uv run vllm --help` 验证

**CUDA driver 报错：**
- 确认用的是 `pytorch-cu118` 源的 torch，不要混用其他源安装的 torch
- `python -c "import torch; print(torch.version.cuda)"` 应输出 `11.8`
