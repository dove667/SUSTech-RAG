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
        self.device_mode = local.device_mode
        self.device_name = local.device_name
        self.gpu_layers = local.gpu_layers
        self.threads = local.threads
        self.threads_batch = local.threads_batch
        self.single_turn = local.single_turn
        self.simple_io = local.simple_io
        self.reasoning = local.reasoning
        self.n_ctx = local.n_ctx
        self.temperature = local.temperature
        self.max_tokens = local.max_tokens
        self.extra_args = local.extra_args

    def generate(self, prompt: str) -> str:
        if not self.model_path:
            raise ValueError("llama.cpp model path is not configured.")
        cmd = [self.binary]
        cmd.extend(self._build_runtime_args())
        cmd.extend(
            [
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
        )
        cmd.extend(self.extra_args)
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        return completed.stdout.strip()

    def _resolve_binary_path(self, raw: str) -> str:
        path = Path(raw)
        if is_windows() and not path.suffix and path.with_suffix(".exe").exists():
            return str(path.with_suffix(".exe"))
        return raw

    def _build_runtime_args(self) -> list[str]:
        args: list[str] = []
        device_arg = self._resolve_device_arg()
        if device_arg is not None:
            args.extend(["--device", device_arg])
        if self.gpu_layers:
            args.extend(["-ngl", str(self.gpu_layers)])
        if self.threads > 0:
            args.extend(["-t", str(self.threads)])
        if self.threads_batch > 0:
            args.extend(["-tb", str(self.threads_batch)])
        if self.single_turn:
            args.append("--single-turn")
        if self.simple_io:
            args.append("--simple-io")
        if self.reasoning:
            args.extend(["--reasoning", self.reasoning])
        return args

    def _resolve_device_arg(self) -> str | None:
        mode = self.device_mode.lower().strip()
        if mode in {"", "auto"}:
            return None
        if mode == "cpu":
            return "none"
        if mode == "custom":
            if not self.device_name:
                raise ValueError("llama.cpp device_mode=custom requires device_name.")
            return self.device_name
        if mode in {"metal", "gpu"}:
            return self.device_name or None
        return self.device_name or mode


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
