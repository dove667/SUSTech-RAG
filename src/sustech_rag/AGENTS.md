# CORE PACKAGE KNOWLEDGE BASE

**OVERVIEW**: Core Python implementation of the SUSTech RAG pipeline, from BFS crawling to reranked generation.

## STRUCTURE

- `cli/`: Command-line interface definitions (Typer).
- `config/`: Configuration schema and YAML loading.
- `crawlers/`: Web scraping and document acquisition.
- `pipeline/`: High-level orchestration and service layer.
- `processing/`: Document cleaning, chunking, and retained PDF parsing code that is not enabled by default.
- `indexing/`: Vector database management (ChromaDB).
- `retrieval/`: Search logic and reranking engine.
- `llm/`: Large Language Model backend abstractions.
- `utils/`: Cross-platform helpers and I/O.

## WHERE TO LOOK

| Task | Location | Key Component |
|------|----------|---------------|
| Add CLI command | `cli/main.py` | `app = Typer()` |
| Change config schema | `config/models.py` | `AppConfig(BaseModel)` |
| Modify scraping logic | `crawlers/site_crawler.py` | `SiteCrawler` class |
| Update pipeline flow | `pipeline/builders.py` | `build_chunks`, `index_documents` |
| Adjust chunking | `processing/chunking.py` | Chunk size/overlap logic |
| Swap embeddings | `indexing/vector_index.py` | `HuggingFaceEmbedding` |
| Tweak reranking | `retrieval/engine.py` | `RetrievalEngine` with BGE |
| Add LLM provider | `llm/backends.py` | `build_llm_backend` factory |
| Path handling | `utils/platform.py` | Windows/Unix path resolution |

## CONVENTIONS

- **Pydantic for Config**: All configuration must be validated through `config.models`.
- **JSONL for Pipeline**: Intermediate data must be stored in `.jsonl` format.
- **Pathlib Only**: Use `pathlib.Path` for all file operations. No string path concatenation.
- **Factory Pattern**: Use `llm/backends.py` or `pipeline/builders.py` for instantiating heavy objects.

## ANTI-PATTERNS

- **NO Direct DB Calls**: Don't call ChromaDB outside of `indexing/`. Use the abstractions.
- **NO Hardcoded Paths**: Never use absolute strings. Reference `config` or `utils.runtime.get_data_dir()`.
- **NO Synchronous Blocking**: Avoid heavy I/O in the main thread during crawling; use the crawler's internal queuing.
- **NO Environment Dependency**: Don't rely on `os.environ` directly in core logic; pass values through `AppConfig`.
