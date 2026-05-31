from __future__ import annotations

from sustech_rag.config.models import AppConfig
from sustech_rag.llm.backends import LlamaCppBackend
from sustech_rag.llm.base import LLMBackend


def create_llm_backend(config: AppConfig) -> LLMBackend:
    backend_name = config.llm.backend.strip().lower()
    if backend_name == "llama_cpp":
        return LlamaCppBackend(config)
    raise ValueError(
        f"Unsupported llm backend: {config.llm.backend!r}. "
        "Expected one of: llama_cpp."
    )
