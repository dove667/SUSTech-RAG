# CONFIGURATION KNOWLEDGE BASE

## OVERVIEW
Runtime configuration for the SUSTech RAG pipeline via YAML files and environment variables.

## WHERE TO LOOK
- `configs/default.yaml`: Primary runtime configuration (crawl, preprocess, index, query).
- `src/sustech_rag/config/loader.py`: Logic for loading YAML and resolving relative paths to absolute.
- `src/sustech_rag/config/models.py`: Pydantic models defining the schema for all sections.
- Environment variables: `SUSTECH_RAG_CONFIG` (config path), `DASHSCOPE_API_KEY`, `LLAMA_CPP_BINARY`, `LLAMA_CPP_MODEL_PATH`.

## CONFIG KEYS

| Section | Key | Description |
|---------|-----|-------------|
| **project** | `data_dir` | Root directory for models, raw data, and vector stores. |
| **crawl** | `seed_urls` | Entry points for the BFS crawler. |
| | `allowed_domains` | Domain whitelist to prevent external crawling. |
| | `max_pages` | Limit on total pages crawled per session. |
| **processing** | `chunk_size` | Character count for text splitting. |
| | `chunk_overlap` | Overlap between consecutive text chunks. |
| | `drop_patterns` | List of substrings (e.g., copyright) to remove during cleaning. |
| **embedding** | `model_name` | HuggingFace model ID for vector embeddings. |
| | `local_path` | Disk location for the embedding model. |
| **retrieval** | `similarity_top_k` | Initial candidates fetched from vector store. |
| | `rerank_top_n` | Final documents passed to LLM after reranking. |
| **vector_store** | `persist_dir` | Local path for ChromaDB storage. |
| **llm** | `backend` | Choice between `llama_cpp` (local) or `dashscope` (cloud). |
| | `local.binary_path` | Optional system path to `llama-cli`; prefer env var `LLAMA_CPP_BINARY`. |
| | `local.model_path` | Path to the GGUF model file. |
| | `local.n_ctx` | Context window size for local inference. |

## NOTES
- Paths in YAML are resolved relative to the config file's location.
- Environment variables take precedence over YAML values for sensitive keys.
- Python 3.11 is required; use `uv` for dependency management.
