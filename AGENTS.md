# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-20
**Commit:** main
**Branch:** main

## OVERVIEW

SUSTech Campus Knowledge Base RAG — Chinese QA system for Southern University of Science and Technology. Crawls public pages → cleans/chunks → embeds → reranks → generates answers via local llama.cpp or DashScope API.

## STRUCTURE

```
RAG/
├── src/sustech_rag/      # Python package (src layout)
│   ├── cli/              # Typer CLI entry (crawl/preprocess/index/query/paths)
│   ├── config/           # YAML config loader + pydantic models
│   ├── crawlers/         # BFS site crawler with readability-lxml
│   ├── pipeline/         # Orchestration: crawl→preprocess→chunk→index builders
│   ├── processing/       # PDF parsing, text cleaning, chunking
│   ├── indexing/         # ChromaDB + HuggingFace embedding
│   ├── retrieval/         # Vector search + BGE reranker
│   ├── llm/              # llama.cpp / DashScope backend abstraction
│   └── utils/            # I/O, platform detection, runtime setup
├── configs/default.yaml  # Runtime pipeline config
├── data/                 # Local models, raw/interim/vector_store
├── tests/                # pytest (pythonpath = src)
└── docs/                 # architecture.md, project-guide.md, runbook.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add CLI command | `src/sustech_rag/cli/main.py` | Typer app, 5 commands |
| Modify pipeline step | `src/sustech_rag/pipeline/builders.py` | crawl_documents, preprocess_documents, build_chunks |
| Change config schema | `src/sustech_rag/config/models.py` | Pydantic models for all config sections |
| Config loading | `src/sustech_rag/config/loader.py` | Resolves relative paths to absolute |
| Retrieval logic | `src/sustech_rag/retrieval/engine.py` | LlamaIndex + reranker |
| LLM backends | `src/sustech_rag/llm/backends.py` | LlamaCpp + DashScope |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `app` | Typer | cli/main.py:12 | CLI root |
| `RagService` | Class | pipeline/rag_service.py | Query orchestration |
| `SiteCrawler` | Class | crawlers/site_crawler.py | BFS crawler |
| `RetrievalEngine` | Class | retrieval/engine.py | Vector + rerank |
| `AppConfig` | Pydantic | config/models.py:67 | Root config model |
| `build_llm_backend` | Func | llm/backends.py:72 | Backend factory |

## CONVENTIONS (THIS PROJECT)

- **Package layout**: src/ (not flat package at root)
- **Python**: Strictly 3.11 (`>=3.11,<3.12`) — 3.10/3.12 not supported
- **Linter**: Ruff (E, F, I, UP, B), line-length=100 — NOT black/yapf
- **Package manager**: uv — NOT pip/poetry
- **Config**: YAML files, not env vars for runtime settings
- **Path handling**: Always pathlib.Path, never os.path.join strings
- **Subprocess**: Always list form `subprocess.run([cmd, arg])`, never shell strings
- **Env override**: LLAMA_CPP_BINARY, LLAMA_CPP_MODEL_PATH, DASHSCOPE_API_KEY env vars override YAML

## ANTI-PATTERNS (THIS PROJECT)

- **DO NOT** hardcode absolute paths — use config + pathlib
- **DO NOT** use `os.system()` or f-string shell commands — subprocess list form only
- **DO NOT** commit data/models/ — already in .gitignore

## UNIQUE STYLES

- Cross-OS: llama-cli.exe resolved automatically on Windows (`is_windows()` check)
- HuggingFace cache: auto-prepare via `prepare_model_cache()` in retrieval/init
- JSONL pipeline: all intermediate results persisted (raw_documents.jsonl, documents.cleaned.jsonl, chunks.jsonl)

## COMMANDS

```bash
uv sync                              # Install dependencies
uv run sustech-rag crawl             # Fetch HTML/PDF
uv run sustech-rag preprocess         # Clean + chunk
uv run sustech-rag index              # Build ChromaDB
uv run sustech-rag query "question"   # Ask RAG
uv run sustech-rag paths             # Show data dirs
uv run pytest                        # Run tests
uv run ruff check src/              # Lint
```

## NOTES

- Models downloaded to `data/models/` on first run (HuggingFace cache)
- `DASHSCOPE_API_KEY` required for cloud inference; local llama.cpp works offline
- Cross-platform paths: all handled via `src/sustech_rag/utils/platform.py`
- Default config: `configs/default.yaml` or `$SUSTECH_RAG_CONFIG` env var
