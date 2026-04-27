# Runbook

## 1. 创建 Python 3.11 环境

```bash
uv python install 3.11
uv venv --python 3.11
uv sync
```

## 2. 配置环境变量

```bash
cp .env.example .env
```

需要时填写：

- `LLAMA_CPP_BINARY`
- `LLAMA_CPP_MODEL_PATH`

## 2.1 本地模型优先目录

默认配置会优先从这些本地目录加载模型：

- `data/models/embeddings/BAAI/bge-small-zh-v1.5`
- `data/models/rerankers/BAAI/bge-reranker-v2-m3`
- `data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf`

## 2.2 llama.cpp 运行方式

### macOS

推荐优先使用系统安装位置，而不是只复制一个 `llama-cli` 文件：

```bash
brew install llama.cpp
brew --prefix llama.cpp
```

Homebrew 常见二进制路径：

```text
/opt/homebrew/opt/llama.cpp/bin/llama-cli
```

如果你想让项目使用 Homebrew 安装位置，可以设置：

```bash
export LLAMA_CPP_BINARY=/opt/homebrew/opt/llama.cpp/bin/llama-cli
```

推荐保持 `configs/default.yaml -> llm.local.binary_path` 为空，优先通过环境变量指定系统安装路径。

### Windows

推荐使用 `llama.cpp` 官方 release 解压目录中的 `llama-cli.exe`，然后把路径填到：

- `LLAMA_CPP_BINARY`
- 或 `configs/default.yaml -> llm.local.binary_path`

### 配置项说明

`configs/default.yaml -> llm.local` 支持这些运行选项：

- `device_mode`
  - `auto`：让 `llama.cpp` 自动选择 GPU 后端
  - `cpu`：强制纯 CPU，等价于 `--device none`
  - `custom`：手动指定 `device_name`
- `device_name`
  - 仅在 `custom` 时使用，原样传给 `--device`
- `gpu_layers`
  - 透传给 `-ngl`
  - `0` 表示不做 GPU 层 offload
  - `auto` 表示交给 `llama.cpp` 自行决定
- `threads` / `threads_batch`
  - CPU 推理线程数
- `single_turn`
  - 是否适合 CLI/程序单轮生成
- `simple_io`
  - 是否启用简化 I/O，适合子进程调用
- `reasoning`
  - `off` / `on` / `auto`
- `extra_args`
  - 额外透传参数列表

### 推荐配置

保守稳定：

```yaml
llm:
  local:
    binary_path: ""
    device_mode: "cpu"
    gpu_layers: "0"
    single_turn: true
    simple_io: true
    reasoning: "off"
```

尝试 GPU / Metal：

```yaml
llm:
  local:
    binary_path: ""
    device_mode: "auto"
    gpu_layers: "auto"
```

指定特定设备：

```yaml
llm:
  local:
    binary_path: ""
    device_mode: "custom"
    device_name: "your-device-name"
```

## 3. 运行数据流程

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

## 4. 提问

```bash
uv run sustech-rag query "南科大本科招生有什么特色？"
```

## 5. 未来增强

- 增加 robots / sitemap 感知
- 增加更强的正文抽取与语言过滤
- 根据机器配置为 reranker / embedding 增加 device 与 batch 参数
- 如果后续实际抓到 PDF，再对 PDF / 招生简章做更细粒度版面处理
