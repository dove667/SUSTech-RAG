# Architecture

## Pipeline

1. `crawl`: 抓取 HTML / PDF 原始内容与元数据
2. `preprocess`: 提取正文、清洗、去重、质量过滤
3. `chunk`: 分块并生成可索引文档
4. `index`: 嵌入并写入 ChromaDB
5. `query`: 相似度召回、重排序、拼接上下文、调用生成模型

## Storage Layout

```text
data/raw/pages/         原始 HTML
data/raw/pdfs/          原始 PDF
data/interim/docs.jsonl 清洗后的文档
data/interim/chunks.jsonl
data/cache/huggingface  embedding / reranker 模型缓存
data/models/            本地 embedding / reranker / GGUF 模型
data/vector_store/
```

## Cross-OS

- 使用 `pathlib.Path`
- 使用 `subprocess.run(list[str])` 代替 shell 拼接
- 显式处理 Windows 下 `llama-cli.exe`
- 所有文本读写统一使用 UTF-8
