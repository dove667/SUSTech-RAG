# PROJECT KNOWLEDGE BASE (DOCS)

**Generated:** 2026-04-20
**Commit:** main
**Branch:** main

## OVERVIEW
Documentation for the SUSTech Campus Knowledge Base RAG project, covering architecture, guides, and operations.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Understand RAG pipeline | `docs/architecture.md` | Flow: crawl → preprocess → chunk → index → query |
| Check storage layout | `docs/architecture.md` | Directory structure for raw, interim, and vector data |
| Browse module roles | `docs/project-guide.md` | Responsibilities of src/sustech_rag subpackages |
| Find configuration keys | `docs/project-guide.md` | Key settings in configs/default.yaml explained |
| Setup environment | `docs/runbook.md` | Python 3.11 + uv setup instructions |
| Run pipeline steps | `docs/runbook.md` | Commands for crawling, indexing, and querying |
| Manage local models | `docs/runbook.md` | Path conventions for BGE and Qwen GGUF models |

## KEY DOCS

| File | Role |
|------|------|
| `docs/architecture.md` | Technical design, data flow, and cross-OS implementation details |
| `docs/project-guide.md` | High-level overview, repo structure, and recommended reading order |
| `docs/runbook.md` | Step-by-step operational guide for setup and execution |

## DATA CONVENTIONS
- `data/raw/`: Original crawler outputs. Current default flow mainly uses HTML; the PDF path is retained but not enabled by default.
- `data/interim/`: Cleaned JSONL files (docs and chunks)
- `data/models/`: Local model storage (Embedding, Reranker, LLM)
- `data/vector_store/`: Persistent ChromaDB index
