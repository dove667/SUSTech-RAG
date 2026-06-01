from __future__ import annotations

from sustech_rag.config.models import AppConfig, LlamaCppConfig, VLLMConfig
from sustech_rag.llm.base import LLMRuntime
from sustech_rag.llm.llama_cpp import LlamaCppClient, LlamaCppLauncher
from sustech_rag.llm.vllm import VLLMClient, VLLMLauncher


def create_llm_runtime(config: AppConfig) -> LLMRuntime:
    if isinstance(config.llm, LlamaCppConfig):
        client = LlamaCppClient(config)
        return LLMRuntime(client=client, launcher=LlamaCppLauncher(config, client))
    if isinstance(config.llm, VLLMConfig):
        client = VLLMClient(config)
        return LLMRuntime(client=client, launcher=VLLMLauncher(config, client))
    raise ValueError(
        f"Unsupported llm backend: {config.llm.backend!r}. "
        "Expected one of: llama_cpp, vllm."
    )
