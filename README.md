# SUSTech Campus Knowledge Base RAG

面向南方科技大学公开信息的中文 Q&A RAG 项目，覆盖抓取、清洗、分块、嵌入、向量检索、重排序和生成的完整 pipeline。

一个适合作为课程项目、研究原型或校园知识库系统起点的本地优先 RAG 工程。

## Highlights

- End-to-end pipeline：从公开网页抓取到本地问答全链路打通
- Local-first：优先使用本地 embedding、reranker、GGUF 模型
- Dual LLM backends：支持 `llama.cpp` 本地推理和 `DashScope API`
- Cross-platform：兼容 macOS / Windows 的路径与执行方式
- Inspectable data flow：每一步都把中间结果落盘，便于调试与复现
- Lightweight stack：`uv + LlamaIndex + ChromaDB`，适合个人开发和教学演示

## 30 秒了解项目

- 数据源：SUSTech 官网、招生页、院系页、校园生活等公开页面
- 向量检索：`LlamaIndex + ChromaDB`
- Embedding：`BAAI/bge-small-zh-v1.5`
- Reranker：`BAAI/bge-reranker-v2-m3`
- 本地生成：`llama.cpp + Qwen3-8B GGUF`
- 备选生成：阿里百炼 `DashScope API`
- 依赖管理：`uv`
- Python 版本：`3.11`

## Project Status

当前仓库已经具备可运行的第一版框架：

- 已完成：项目结构、CLI、抓取、清洗、分块、索引、检索、重排序、本地 / API 双生成后端
- 已完成：本地模型优先加载、跨平台路径处理、基础测试与文档
- 进行中：真实数据抓取验证、清洗规则增强、rerank / 召回质量调优
- 计划中：更强的网页解析、增量更新、评测集与离线评估

## Demo Flow

```text
SUSTech Public Pages / PDFs
          ->
       Crawl
          ->
     Clean + Filter
          ->
        Chunk
          ->
   Embed + ChromaDB
          ->
 Retrieve + Rerank
          ->
   Local Qwen / API
```

## 快速开始

```bash
uv sync
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag query "南科大宿舍申请流程是什么？"
```

## Tech Stack

- Runtime: `Python 3.11`
- Package manager: `uv`
- Crawling: `httpx + BeautifulSoup + readability-lxml + pypdf`
- RAG orchestration: `LlamaIndex`
- Vector store: `ChromaDB`
- Embedding: `BAAI/bge-small-zh-v1.5`
- Reranking: `BAAI/bge-reranker-v2-m3`
- Local inference: `llama.cpp + Qwen3-8B GGUF`
- Optional API inference: `DashScope`

## 你最需要知道的目录

```text
configs/default.yaml          主配置
src/sustech_rag/cli/          CLI 入口
src/sustech_rag/crawlers/     网页抓取
src/sustech_rag/processing/   清洗、PDF 解析、分块
src/sustech_rag/indexing/     嵌入与向量索引
src/sustech_rag/retrieval/    召回与重排序
src/sustech_rag/llm/          llama.cpp / DashScope 后端
data/models/                  本地模型目录
data/raw/                     原始抓取结果
data/interim/                 清洗与分块中间结果
data/vector_store/            ChromaDB 数据
docs/project-guide.md         项目结构总览
```

## 默认本地模型位置

```text
data/models/embeddings/BAAI/bge-small-zh-v1.5
data/models/rerankers/BAAI/bge-reranker-v2-m3
data/models/llama.cpp/llama-cli
data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf
```

## Repository Layout

如果你是第一次进这个仓库，建议优先看：

1. [configs/default.yaml](/Users/dove/Desktop/LLM/RAG/configs/default.yaml)
2. [src/sustech_rag/cli/main.py](/Users/dove/Desktop/LLM/RAG/src/sustech_rag/cli/main.py)
3. [src/sustech_rag/pipeline/builders.py](/Users/dove/Desktop/LLM/RAG/src/sustech_rag/pipeline/builders.py)
4. [src/sustech_rag/pipeline/rag_service.py](/Users/dove/Desktop/LLM/RAG/src/sustech_rag/pipeline/rag_service.py)
5. [docs/project-guide.md](/Users/dove/Desktop/LLM/RAG/docs/project-guide.md)

## 典型工作流

1. `crawl`
   抓取 HTML / PDF 原始数据并保存到本地。
2. `preprocess`
   提取正文、清洗噪声、质量过滤，并切分成 chunk。
3. `index`
   生成 embedding，写入本地 ChromaDB。
4. `query`
   先做相似度召回，再做 rerank，最后调用本地或 API 模型生成答案。

## 进一步阅读

- 项目结构与模块说明：[docs/project-guide.md](/Users/dove/Desktop/LLM/RAG/docs/project-guide.md)
- 架构说明：[docs/architecture.md](/Users/dove/Desktop/LLM/RAG/docs/architecture.md)
- 运行说明：[docs/runbook.md](/Users/dove/Desktop/LLM/RAG/docs/runbook.md)

## 备注

- 项目优先保证全链路清晰、可维护、跨 macOS / Windows 兼容
- 模型和数据目录默认不提交到 GitHub
- 真正执行抓取、模型下载和 API 调用时需要联网

## Roadmap

- 改进站点抓取策略，补充 sitemap / robots / 增量更新支持
- 提升正文抽取与页面去噪质量
- 加入真实评测集与 RAG 指标评估
- 增加 API 服务层或 Web UI
- 支持更多高校知识库数据源

## Contributing

欢迎把这个仓库当作课程项目底座或继续扩展的开源原型。

- 先阅读 [docs/project-guide.md](/Users/dove/Desktop/LLM/RAG/docs/project-guide.md)
- 运行前先检查 [docs/runbook.md](/Users/dove/Desktop/LLM/RAG/docs/runbook.md)
- 提交前尽量保持配置、文档和代码同步更新

更具体的协作说明见 [CONTRIBUTING.md](/Users/dove/Desktop/LLM/RAG/CONTRIBUTING.md)。
