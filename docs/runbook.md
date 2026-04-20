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

- `DASHSCOPE_API_KEY`
- `LLAMA_CPP_BINARY`
- `LLAMA_CPP_MODEL_PATH`

## 2.1 本地模型优先目录

默认配置会优先从这些本地目录加载模型：

- `data/models/embeddings/BAAI/bge-small-zh-v1.5`
- `data/models/rerankers/BAAI/bge-reranker-v2-m3`
- `data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf`
- `data/models/llama.cpp/llama-cli` 或 Windows 下 `llama-cli.exe`

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
- 对 PDF / 招生简章做更细粒度版面处理
