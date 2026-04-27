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
SUSTech Public Pages
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
- Crawling: `httpx + BeautifulSoup + readability-lxml`
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
src/sustech_rag/processing/   清洗、分块、保留的 PDF 解析代码
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
data/models/llm/qwen/Qwen3-8B-Q4_K_M.gguf
```

## llama.cpp Runtime Options

`llm.local` 下面现在可以直接配置 `llama.cpp` 运行参数：

- `binary_path`：`llama-cli` 路径
- `model_path`：GGUF 模型路径
- `device_mode`：`auto`、`cpu`、`custom`
- `device_name`：当 `device_mode=custom` 时传给 `--device` 的原始值
- `gpu_layers`：传给 `-ngl`
- `threads` / `threads_batch`：CPU 线程数
- `single_turn`：是否单轮输出
- `simple_io`：是否使用简化 I/O
- `reasoning`：`off`、`on`、`auto`
- `extra_args`：额外原样透传给 `llama-cli`

推荐：

- macOS 首次调试：`device_mode: cpu`
- `binary_path` 建议留空，并通过 `LLAMA_CPP_BINARY` 指向系统安装目录
- macOS 想尝试 Metal：`device_mode: auto`，并把 `gpu_layers` 改成 `auto` 或较大的数字
- Windows / Linux GPU：优先用 `device_mode: auto`，必要时改 `custom + device_name`

## Repository Layout

如果你是第一次进这个仓库，建议优先看：

1. [configs/default.yaml](configs/default.yaml)
2. [src/sustech_rag/cli/main.py](src/sustech_rag/cli/main.py)
3. [src/sustech_rag/pipeline/builders.py](src/sustech_rag/pipeline/builders.py)
4. [src/sustech_rag/pipeline/rag_service.py](src/sustech_rag/pipeline/rag_service.py)
5. [docs/project-guide.md](docs/project-guide.md)

## 典型工作流

1. `crawl`
   目前默认抓取 HTML 原始数据并保存到本地。
2. `preprocess`
   提取正文、清洗噪声、质量过滤，并切分成 chunk。
3. `index`
   生成 embedding，写入本地 ChromaDB。
4. `query`
   先做相似度召回，再做 rerank，最后调用本地或 API 模型生成答案。

## 进一步阅读

- 项目结构与模块说明：[docs/project-guide.md](docs/project-guide.md)
- 架构说明：[docs/architecture.md](docs/architecture.md)
- 运行说明：[docs/runbook.md](docs/runbook.md)

## 备注

- 项目优先保证全链路清晰、可维护、跨 macOS / Windows 兼容
- 模型和数据目录默认不提交到 GitHub
- 真正执行抓取、模型下载和 API 调用时需要联网
- PDF 抓取与解析代码仍然保留，但当前默认配置已关闭；在目前的学校站点测试中，crawler 也尚未实际抓到 PDF 文件

## Roadmap

- 改进站点抓取策略，补充 sitemap / robots / 增量更新支持
- 提升正文抽取与页面去噪质量
- 加入真实评测集与 RAG 指标评估
- 增加 API 服务层或 Web UI
- 支持更多高校知识库数据源

## Contributing

欢迎把这个仓库当作课程项目底座或继续扩展的开源原型。

- 先阅读 [docs/project-guide.md](docs/project-guide.md)
- 运行前先检查 [docs/runbook.md](docs/runbook.md)
- 提交前尽量保持配置、文档和代码同步更新

更具体的协作说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。
