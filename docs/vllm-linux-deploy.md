# vLLM Linux 部署

本文针对下面这类部署方式：

- 同一台 Linux 服务器同时运行 `backend` 和 `vLLM`
- `backend` 与 `vLLM` 默认共用同一个环境
- 启动入口仍然只有一个：`uv run sustech-rag serve`
- 目标机器：`4 * RTX 4090`
- 目标模型：`Qwen/Qwen3.6-35B-A3B-FP8`
- 推荐检索模型：`Qwen/Qwen3-Embedding-4B` + `Qwen/Qwen3-Reranker-4B`

## 1. 总体结构

推荐目录：

```text
/srv/sustech-rag/
  app/                         本仓库
```

职责分工：

- `backend` 环境：安装本项目后端依赖，同时在 Linux 上自动安装 `vllm==0.21.0`
- `app/backend/configs/vllm.linux.example.yaml`：告诉 backend 如何启动同环境中的 `vllm serve`

## 2. 准备 backend 环境

```bash
cd /srv/sustech-rag/app/backend
conda create -n backend python=3.11 -y
conda activate backend
pip install -U pip
pip install uv
uv sync
```

如需测试和 lint：

```bash
uv sync --extra dev
```
在 Linux 上，`vllm==0.21.0` 已经通过 `pyproject.toml` 的平台条件依赖自动加入当前环境；在 macOS / Windows 上则不会安装。

确认可执行文件存在：

```bash
which vllm
vllm --help
```

## 3. 准备索引与辅助模型

以下步骤使用 `backend` 环境执行：

```bash
conda activate backend
cd /srv/sustech-rag/app/backend
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

如果你已经提前准备好了 `data/` 目录，也可以直接复用，不必重新抓取和建库。

如果这台 Linux 服务器主要承担正式推理服务，我建议把样例配置里的检索模型也一起切到：

- `embedding.model_name: Qwen/Qwen3-Embedding-4B`
- `retrieval.reranker_model: Qwen/Qwen3-Reranker-4B`

对应的样例文件已经按这组模型更新好了。

## 4. 准备 vLLM 配置

复制一份样例配置：

```bash
cd /srv/sustech-rag/app/backend
cp configs/vllm.linux.example.yaml configs/vllm.qwen35b.yaml
```

建议至少检查这些字段：

```yaml
embedding:
  model_name: "Qwen/Qwen3-Embedding-4B"
  local_path: "data/models/embeddings/Qwen/Qwen3-Embedding-4B"
  batch_size: 4
  device: ""
  dtype: "bfloat16"

retrieval:
  reranker_model: "Qwen/Qwen3-Reranker-4B"
  reranker_local_path: "data/models/rerankers/Qwen/Qwen3-Reranker-4B"
  reranker_device: ""
  reranker_dtype: "bfloat16"

llm:
  backend: "vllm"
  temperature: 0.2
  max_tokens: 1024
  max_concurrent_requests: 32
  server_port: 8081
  binary_path: ""
  model_name: "Qwen/Qwen3.6-35B-A3B-FP8"
  served_model_name: "qwen3.6-35b-a3b-fp8"
  dtype: "auto"
  tensor_parallel_size: 4
  distributed_executor_backend: "mp"
  max_model_len: 32768
  max_num_seqs: 32
  max_num_batched_tokens: 12288
  reasoning_parser: "qwen3"
```

当前样例已经把这两个小模型的 dtype 备注成 `bfloat16`。`device` 先留空，表示继续走底层库默认设备选择。

这点需要特别注意：

- 现在代码里如果 `device` 留空，`SentenceTransformer` / `CrossEncoder` 会在检测到 CUDA 时优先用 GPU
- 这通常等价于落到“当前可见的第一张卡”，实践里可以理解成 `cuda:0`
- 但如果 `vLLM` 已经用 `tensor_parallel_size: 4` 占满 4 张 4090，就不建议再默认把这两个小模型塞进 `cuda:0`

更稳的做法通常是二选一：

- 保持 `device: ""` 和 `reranker_device: ""`，让它们跑 CPU
- 或者明确写成 `cuda:0` / `cuda:1`，但前提是你给 `vLLM` 留了显存余量，或者本来就没把 4 张卡全部占满

## 5. 为什么先用 FP8

对 `4 * 4090` 来说，我建议先从 `Qwen/Qwen3.6-35B-A3B-FP8` 起步，原因很实际：

- 显存压力更小，给 KV cache 和 batch 调度留更多余量
- 更适合先把服务稳定跑起来
- 当前项目检索链路本身已经占用一定 CPU/内存资源，LLM 侧保守一些更稳

如果你后续实测发现非 `FP8` 版本更适合你的负载，只需要把：

```yaml
llm:
  model_name: "Qwen/Qwen3.6-35B-A3B"
  served_model_name: "qwen3.6-35b-a3b"
```

改掉即可，其他大部分参数可以保持不变。

## 6. 启动服务

只需要启动 backend：

```bash
conda activate backend
cd /srv/sustech-rag/app/backend
uv run sustech-rag serve --host 0.0.0.0 --port 8001 --config configs/vllm.qwen35b.yaml
```

backend 会自动读取配置中的：

- `llm.backend: vllm`
- `llm.binary_path`

如果 `llm.binary_path` 为空，backend 会直接拉起当前环境里的 `vllm serve ...`。
只有在你想显式指向另一个可执行文件时，才需要填写 `binary_path`。

也就是说，最终仍然是一条命令启动完整服务。

## 7. 健康检查

后端：

```bash
curl http://127.0.0.1:8001/api/health
```

如果配置正常，backend 内部会先等 `vLLM` 就绪，再对外返回 ready。

## 8. 常见调整

吞吐偏低：

- 先调大 `llm.max_num_seqs`
- 再观察 `llm.max_concurrent_requests`
- 确认 `tensor_parallel_size: 4` 已生效
- 如果显存主要给生成模型，`embedding.batch_size` 可以先保持 `4`

显存吃紧：

- 先降低 `max_model_len`
- 再降低 `max_num_batched_tokens`
- 最后再降低 `max_num_seqs`
- 如果检索模型也放在同机 GPU 上，可以再把 `embedding.batch_size` 调小
- 如果检索模型要上 GPU，优先显式写 `embedding.device` 和 `retrieval.reranker_device`，不要隐式赌默认卡位

启动慢：

- 35B 级别模型首启较慢是正常现象
- `vLLM` 的 warm-up 完成后，后续请求会稳定很多

找不到 `vllm`：

- 先执行 `which vllm`
- 如果 `llm.binary_path` 非空，再检查它是否指向真实文件
- 手动运行一次 `vllm --help`

## 9. 推荐的最小上线流程

1. 在服务器上准备好一个 `backend` 环境。
2. 在这个环境里执行 `uv sync`，让 `vllm==0.21.0` 随 Linux 平台依赖一起装好。
3. 用这个环境完成建索引和配置检查。
4. 默认保持 `configs/vllm.qwen35b.yaml` 中的 `binary_path: ""`。
5. 执行 `uv run sustech-rag serve --config configs/vllm.qwen35b.yaml`。
6. 用 `/api/health` 和前端实际对话做验收。
