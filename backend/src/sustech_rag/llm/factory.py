from __future__ import annotations

from sustech_rag.config.models import AppConfig, LlamaCppConfig, VLLMConfig
from sustech_rag.llm.backends import LlamaCppBackend
from sustech_rag.llm.base import LLMBackend
from sustech_rag.llm.vllm_backend import VLLMBackend


def create_llm_backend(config: AppConfig) -> LLMBackend:
    if isinstance(config.llm, LlamaCppConfig):
        return LlamaCppBackend(config)
    if isinstance(config.llm, VLLMConfig):
        return VLLMBackend(config)
    raise ValueError(
        f"Unsupported llm backend: {config.llm.backend!r}. "
        "Expected one of: llama_cpp, vllm."
    )
