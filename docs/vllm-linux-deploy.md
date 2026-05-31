# vLLM Linux 部署

本文针对下面这类部署方式：

- 同一台 Linux 服务器同时运行 `backend` 和 `vLLM`
- `backend` 与 `vLLM` 使用不同的 conda 环境
- 启动入口仍然只有一个：`uv run sustech-rag serve`
- 目标机器：`4 * RTX 4090`
- 目标模型：`Qwen/Qwen3.6-35B-A3B-FP8`

## 1. 总体结构

推荐目录：

```text
/srv/sustech-rag/
  app/                         本仓库
```

职责分工：

- `backend` conda 环境：安装本项目后端依赖、运行 `uv run sustech-rag serve`
- `vllm-0.21` conda 环境：只安装 `vllm==0.21.0` 及其 CUDA 相关依赖
- `app/backend/configs/vllm.linux.example.yaml`：告诉 backend 去启动 `vllm-0.21/bin/vllm`

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

## 3. 准备 vLLM 环境

```bash
conda create -n vllm-0.21 python=3.11 -y
conda activate vllm-0.21
pip install -U pip
pip install vllm==0.21.0
```

安装完成后，确认可执行文件存在：

```bash
~/miniconda3/envs/vllm-0.21/bin/vllm --help
```

## 4. 准备索引与辅助模型

以下步骤使用 `backend` 环境执行：

```bash
conda activate backend
cd /srv/sustech-rag/app/backend
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

如果你已经提前准备好了 `data/` 目录，也可以直接复用，不必重新抓取和建库。

## 5. 准备 vLLM 配置

复制一份样例配置：

```bash
cd /srv/sustech-rag/app/backend
cp configs/vllm.linux.example.yaml configs/vllm.qwen35b.yaml
```

建议至少检查这些字段：

```yaml
llm:
  backend: "vllm"
  temperature: 0.2
  max_tokens: 1024
  max_concurrent_requests: 32
  server_port: 8081
  binary_path: "~/miniconda3/envs/vllm-0.21/bin/vllm"
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

## 6. 为什么先用 FP8

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

## 7. 启动服务

只需要启动 backend：

```bash
conda activate backend
cd /srv/sustech-rag/app/backend
uv run sustech-rag serve --host 0.0.0.0 --port 8000 --config configs/vllm.qwen35b.yaml
```

backend 会自动读取配置中的：

- `llm.backend: vllm`
- `llm.binary_path`

然后拉起 `~/miniconda3/envs/vllm-0.21/bin/vllm serve ...`。

也就是说，最终仍然是一条命令启动完整服务。

## 8. 健康检查

后端：

```bash
curl http://127.0.0.1:8000/api/health
```

如果配置正常，backend 内部会先等 `vLLM` 就绪，再对外返回 ready。

## 9. 常见调整

吞吐偏低：

- 先调大 `llm.max_num_seqs`
- 再观察 `llm.max_concurrent_requests`
- 确认 `tensor_parallel_size: 4` 已生效

显存吃紧：

- 先降低 `max_model_len`
- 再降低 `max_num_batched_tokens`
- 最后再降低 `max_num_seqs`

启动慢：

- 35B 级别模型首启较慢是正常现象
- `vLLM` 的 warm-up 完成后，后续请求会稳定很多

找不到 `vllm`：

- 检查 `llm.binary_path` 是否指向真实文件
- 手动运行一次 `~/miniconda3/envs/vllm-0.21/bin/vllm --help`

## 10. 推荐的最小上线流程

1. 在服务器上准备好两个 conda 环境。
2. 用 `backend` 环境完成 `uv sync`、建索引和配置检查。
3. 用 `vllm-0.21` 环境安装 `vllm==0.21.0`。
4. 修改 `configs/vllm.qwen35b.yaml` 中的 `binary_path`。
5. 执行 `uv run sustech-rag serve --config configs/vllm.qwen35b.yaml`。
6. 用 `/api/health` 和前端实际对话做验收。
