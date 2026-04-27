# Project Guide

## 项目目标

这个项目用于构建一个面向南方科技大学公开知识的本地 RAG 系统：

- 抓取公开网页
- 清洗、过滤并切分成适合检索的文本块
- 用中文 embedding 建立本地向量库
- 用 reranker 做精筛
- 用本地 `llama.cpp` 或百炼 API 生成答案

## 一图看懂

```text
Public Web
        |
        v
     crawl
        |
        v
   preprocess
        |
        v
      chunk
        |
        v
      index
        |
        v
 retrieve + rerank
        |
        v
     generate
```

## 仓库结构

```text
.
├── configs/
│   └── default.yaml
├── data/
│   ├── cache/
│   ├── interim/
│   ├── models/
│   ├── raw/
│   └── vector_store/
├── docs/
│   ├── architecture.md
│   ├── project-guide.md
│   └── runbook.md
├── scripts/
│   └── run_pipeline.py
├── src/sustech_rag/
│   ├── cli/
│   ├── config/
│   ├── crawlers/
│   ├── indexing/
│   ├── llm/
│   ├── pipeline/
│   ├── processing/
│   ├── retrieval/
│   └── utils/
├── tests/
├── pyproject.toml
└── uv.lock
```

## 代码入口

主 CLI 在 [src/sustech_rag/cli/main.py](../src/sustech_rag/cli/main.py)。

常用命令：

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag query "南科大本科招生有什么特色？"
```

## 各模块职责

`src/sustech_rag/config/`
负责读取 YAML 配置，并解析成本地绝对路径。

`src/sustech_rag/crawlers/`
负责从 SUSTech 公开站点抓取 HTML，并保存原始文件。PDF 路径仍然保留为可选开发项。

`src/sustech_rag/processing/`
负责正文清洗、噪声过滤和文本分块。PDF 文本提取代码目前保留但默认未启用。

`src/sustech_rag/pipeline/`
负责把 crawl、preprocess、chunk、answer 这些步骤串起来。

`src/sustech_rag/indexing/`
负责 embedding 与 ChromaDB 索引写入。

`src/sustech_rag/retrieval/`
负责相似度召回和 `BGE-Reranker-v2-M3` 重排序。

`src/sustech_rag/llm/`
负责本地 `llama.cpp` 的统一调用接口。

`src/sustech_rag/utils/`
负责 I/O、平台差异、模型缓存目录等基础工具。

## 数据目录约定

`data/raw/`
原始抓取结果目前以 HTML 为主。`raw/pdfs/` 目录和相关代码仍保留，但当前默认配置未启用 PDF 抓取，且现阶段测试中 crawler 也尚未实际抓到 PDF。

`data/interim/`
清洗后的文档与 chunks，例如 `documents.cleaned.jsonl`、`chunks.jsonl`。

`data/vector_store/`
ChromaDB 本地向量库。

`data/cache/huggingface/`
Hugging Face 缓存目录。

`data/models/`
本地 embedding、reranker 和 GGUF 模型目录，优先于在线下载。

## 配置里最重要的几项

配置文件在 [configs/default.yaml](../configs/default.yaml)。

建议优先关注：

- `crawl.seed_urls`
- `crawl.allowed_domains`
- `processing.chunk_size`
- `processing.chunk_overlap`
- `embedding.local_path`
- `retrieval.reranker_local_path`
- `llm.backend`
- `llm.local.binary_path`
- `llm.local.model_path`

## 首次阅读顺序

如果你想用最少时间理解项目，建议按这个顺序看：

1. [README.md](../README.md)
2. [configs/default.yaml](../configs/default.yaml)
3. [src/sustech_rag/cli/main.py](../src/sustech_rag/cli/main.py)
4. [src/sustech_rag/pipeline/builders.py](../src/sustech_rag/pipeline/builders.py)
5. [src/sustech_rag/pipeline/rag_service.py](../src/sustech_rag/pipeline/rag_service.py)
6. 再根据需要看 `crawlers/`、`processing/`、`retrieval/`

## 上传 GitHub 前

建议提交：

- `src/`
- `tests/`
- `configs/`
- `docs/`
- `pyproject.toml`
- `uv.lock`
- `README.md`

不要提交：

- `.venv/`
- `.uv-cache/`
- `data/raw/`
- `data/interim/`
- `data/vector_store/`
- `data/cache/`
- `data/models/`
- `.env`
