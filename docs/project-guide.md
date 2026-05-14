# Project Guide

这份导览帮助新贡献者快速理解后端代码。先看 CLI，再看 pipeline，最后按需进入抓取、清洗、索引、检索和 LLM 细节。

## 推荐阅读顺序

1. [../configs/default.yaml](../configs/default.yaml)
2. [../src/sustech_rag/cli/main.py](../src/sustech_rag/cli/main.py)
3. [../src/sustech_rag/pipeline/builders.py](../src/sustech_rag/pipeline/builders.py)
4. [../src/sustech_rag/pipeline/rag_service.py](../src/sustech_rag/pipeline/rag_service.py)
5. [../src/sustech_rag/api/app.py](../src/sustech_rag/api/app.py)
6. [../src/sustech_rag/api/routes.py](../src/sustech_rag/api/routes.py)

## CLI 命令

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
uv run sustech-rag query "问题"
uv run sustech-rag serve --host 127.0.0.1 --port 8000
uv run sustech-rag paths
```

`preprocess` 会同时执行清洗和分块；`index` 读取 `data/interim/chunks.jsonl`。
`query` 是端到端冒烟测试入口，会临时启动并关闭 `llama-server`。长时间交互使用 `serve`。

## 核心数据结构

- `RawDocument`：抓取后的一篇原始文档，包含 URL、标题、正文、content type、source path 和 metadata。
- `ChunkedDocument`：可索引的文本块，包含 chunk id、doc id、标题、文本、来源 URL 和 metadata。
- `RetrievedChunk`：检索/重排序结果，包含文本、score 和 metadata。
- `AppConfig`：完整应用配置。

## 开发约定

- 新的数据文件优先写到 `data/raw` 或 `data/interim`。
- 新的运行参数优先进入 `configs/default.yaml` 和 `config/models.py`。
- 业务入口优先通过 CLI 或 `RagService` 暴露，不要让 API 路由直接拼 pipeline。
- Chroma 客户端统一走 `utils/chroma_client.py`，避免 settings 不一致。
- 不提交模型、缓存、抓取结果和向量库。

## 测试位置

```text
tests/test_config.py
tests/test_site_crawler.py
tests/test_cleaning.py
tests/test_chunking.py
tests/test_builders.py
tests/test_indexing.py
tests/test_api.py
```

新增功能建议至少覆盖：

- 配置解析或默认值
- 输入/输出文件路径
- API schema 和错误响应
- 对 Chroma、LLM、网络请求的 mock 行为
