"""
Download embedding, reranker, and GGUF weights into backend/data/models/ (paths match configs/default.yaml).

Usage (from repo root or backend/):
  cd backend && uv run python scripts/download_models.py
"""
from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    root = _BACKEND_ROOT
    emb = root / "data" / "models" / "embeddings" / "BAAI" / "bge-small-zh-v1.5"
    rer = root / "data" / "models" / "rerankers" / "BAAI" / "bge-reranker-v2-m3"
    llm_dir = root / "data" / "models" / "llm" / "qwen"
    gguf_name = "Qwen3-8B-Q4_K_M.gguf"

    emb.mkdir(parents=True, exist_ok=True)
    rer.mkdir(parents=True, exist_ok=True)
    llm_dir.mkdir(parents=True, exist_ok=True)

    print("1/3 Embedding BAAI/bge-small-zh-v1.5 ->", emb)
    snapshot_download("BAAI/bge-small-zh-v1.5", local_dir=str(emb))

    print("2/3 Reranker BAAI/bge-reranker-v2-m3 ->", rer)
    snapshot_download("BAAI/bge-reranker-v2-m3", local_dir=str(rer))

    print("3/3 LLM Qwen/Qwen3-8B-GGUF", gguf_name, "->", llm_dir)
    hf_hub_download(
        repo_id="Qwen/Qwen3-8B-GGUF",
        filename=gguf_name,
        local_dir=str(llm_dir),
    )

    out_gguf = llm_dir / gguf_name
    if not out_gguf.is_file():
        # hf_hub_download may place under subdir in some versions
        candidates = list(llm_dir.rglob(gguf_name))
        if not candidates:
            raise SystemExit(f"GGUF not found under {llm_dir}")
        out_gguf = candidates[0]
    print("Done. GGUF at:", out_gguf.resolve())


if __name__ == "__main__":
    main()
