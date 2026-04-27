from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import dashscope

from sustech_rag.config.models import AppConfig
from sustech_rag.utils.platform import default_llama_binary_name, is_windows


class LLMBackend(ABC):
    """
    LLM 后端抽象基类。
    定义所有大语言模型后端的统一接口。
    输入参数：无。
    输出参数：用于实现统一生成能力的后端抽象对象。
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        生成文本结果。
        接收提示词并返回模型生成内容的统一接口。
        输入参数：prompt，用户输入的提示词文本。
        输出参数：模型生成的文本结果。
        """
        raise NotImplementedError


class LlamaCppBackend(LLMBackend):
    def __init__(self, config: AppConfig) -> None:
        """
        初始化 llama.cpp 后端。
        根据配置和环境变量准备本地 llama.cpp 推理所需参数。
        输入参数：config，应用配置对象，包含 LLM 本地后端相关设置。
        输出参数：无，完成实例属性初始化。
        """
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
        """
        调用 llama.cpp 生成文本。
        组装命令行参数并执行本地 llama.cpp 进程生成回复。
        输入参数：prompt，用户输入的提示词文本。
        输出参数：llama.cpp 返回并清理后的文本结果。
        """
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
        """
        解析 llama.cpp 可执行文件路径。
        在 Windows 环境下自动补全 .exe 后缀并返回可执行路径。
        输入参数：raw，原始二进制文件路径或文件名。
        输出参数：解析后的可执行文件路径。
        """
        path = Path(raw)
        if is_windows() and not path.suffix and path.with_suffix(".exe").exists():
            return str(path.with_suffix(".exe"))
        return raw

    def _build_runtime_args(self) -> list[str]:
        """
        构建 llama.cpp 运行参数。
        根据设备模式、GPU 层数、线程数及输出模式生成运行参数列表。
        输入参数：无。
        输出参数：llama.cpp 命令行参数列表。
        """
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
        """
        解析设备参数值。
        将配置中的 device_mode 转换为 llama.cpp 可接受的 --device 参数。
        输入参数：无。
        输出参数：可用的设备参数字符串，或在自动模式下返回 None。
        """
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
        """
        初始化 DashScope 后端。
        读取 DashScope 模型配置并设置 API 密钥。
        输入参数：config，应用配置对象，包含 DashScope 相关设置。
        输出参数：无，完成实例属性初始化。
        """
        self.model = config.llm.dashscope.model
        self.temperature = config.llm.dashscope.temperature
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")

    def generate(self, prompt: str) -> str:
        """
        调用 DashScope 生成文本。
        通过 DashScope Generation API 发送提示词并返回生成结果。
        输入参数：prompt，用户输入的提示词文本。
        输出参数：DashScope 返回并清理后的文本结果。
        """
        response = dashscope.Generation.call(
            model=self.model,
            prompt=prompt,
            temperature=self.temperature,
        )
        return response.output.text.strip()


def build_llm_backend(config: AppConfig) -> LLMBackend:
    """
    构建 LLM 后端实例。
    根据配置选择并创建 DashScope 或 llama.cpp 后端实现。
    输入参数：config，应用配置对象，包含 LLM 后端类型与参数。
    输出参数：已初始化的 LLMBackend 实例。
    """
    if config.llm.backend == "dashscope":
        return DashScopeBackend(config)
    return LlamaCppBackend(config)
