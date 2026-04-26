# Contributing

感谢你愿意改进这个项目。

## 开始之前

建议先阅读：

1. [README.md](/Users/dove/Desktop/LLM/RAG/README.md)
2. [docs/project-guide.md](/Users/dove/Desktop/LLM/RAG/docs/project-guide.md)
3. [docs/runbook.md](/Users/dove/Desktop/LLM/RAG/docs/runbook.md)

## 本地开发

```bash
uv sync --extra dev
uv run pytest
```

如果你要跑完整流程：

```bash
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

## 提交建议

- 保持改动聚焦，避免把不相关调整混在一起
- 修改配置或目录约定时，请同步更新文档
- 新增模块时，尽量沿用现有目录边界
- 涉及跨平台行为时，请避免写死平台路径和 shell 语法

## 不要提交

- `.venv/`
- `.uv-cache/`
- `data/raw/`
- `data/interim/`
- `data/vector_store/`
- `data/cache/`
- `data/models/`
- `.env`

## 可以贡献的方向

- 更好的网页抓取与正文抽取
- 更细致的清洗和去重规则
- 更高质量的 chunking 策略
- 检索和 rerank 效果评估
- Web UI / API 服务化
- 文档、示例和教学材料
