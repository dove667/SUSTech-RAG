from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import dashscope

from sustech_rag.config.models import AppConfig
from sustech_rag.utils.platform import default_llama_binary_name, is_windows


class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class LlamaCppBackend(LLMBackend):
    def __init__(self, config: AppConfig) -> None:
        local = config.llm.local
        self.binary = self._resolve_binary_path(
            os.getenv("LLAMA_CPP_BINARY") or local.binary_path or default_llama_binary_name()
        )
        self.model_path = os.getenv("LLAMA_CPP_MODEL_PATH") or local.model_path
        self.n_ctx = local.n_ctx
        self.temperature = local.temperature
        self.max_tokens = local.max_tokens

    def generate(self, prompt: str) -> str:
        if not self.model_path:
            raise ValueError("llama.cpp model path is not configured.")
        cmd = [
            self.binary,
            "-m",
            self.model_path,
            "-c",
            str(self.n_ctx),
            "-n",
            str(self.max_tokens),
            "--temp",
            str(self.temperature),
            "-p",
            prompt,
        ]
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        return completed.stdout.strip()

    def _resolve_binary_path(self, raw: str) -> str:
        path = Path(raw)
        if is_windows() and not path.suffix and path.with_suffix(".exe").exists():
            return str(path.with_suffix(".exe"))
        return raw


class DashScopeBackend(LLMBackend):
    def __init__(self, config: AppConfig) -> None:
        self.model = config.llm.dashscope.model
        self.temperature = config.llm.dashscope.temperature
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")

    def generate(self, prompt: str) -> str:
        response = dashscope.Generation.call(
            model=self.model,
            prompt=prompt,
            temperature=self.temperature,
        )
        return response.output.text.strip()


def build_llm_backend(config: AppConfig) -> LLMBackend:
    if config.llm.backend == "dashscope":
        return DashScopeBackend(config)
    return LlamaCppBackend(config)
