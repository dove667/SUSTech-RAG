"""Download model weights into backend/data/models."""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def download_models() -> None:
    """Download embedding, reranker, and GGUF weights."""
    emb = _BACKEND_ROOT / "data" / "models" / "embeddings" / "BAAI" / "bge-small-zh-v1.5"
    rer = _BACKEND_ROOT / "data" / "models" / "rerankers" / "BAAI" / "bge-reranker-v2-m3"
    llm_dir = _BACKEND_ROOT / "data" / "models" / "llm" / "qwen"
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
        candidates = list(llm_dir.rglob(gguf_name))
        if not candidates:
            raise SystemExit(f"GGUF not found under {llm_dir}")
        out_gguf = candidates[0]
    print("Done. GGUF at:", out_gguf.resolve())


def main() -> None:
    download_models()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
