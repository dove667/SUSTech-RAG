from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx

from sustech_rag.config.models import AppConfig, LlamaCppConfig
from sustech_rag.llm.base import OpenAICompatibleClientBase, OpenAICompatibleEndpoint


class LlamaCppClient(OpenAICompatibleClientBase):
    """OpenAI-compatible llama.cpp client; does not manage the server process."""

    def __init__(self, config: AppConfig) -> None:
        if not isinstance(config.llm, LlamaCppConfig):
            raise TypeError("LlamaCppClient requires a llama_cpp configuration.")
        super().__init__(
            endpoint=OpenAICompatibleEndpoint(
                model_path=config.llm.model_path,
                host="127.0.0.1",
                port=config.llm.server_port,
            ),
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            stop=config.llm.stop,
        )

    def _request_label(self) -> str:
        return "llama-server"

    def _malformed_sse_label(self) -> str:
        return "SSE JSON"


class LlamaCppLauncher:
    """Managed llama.cpp launcher; keeps warm-up behavior here."""

    def __init__(self, config: AppConfig, client: LlamaCppClient) -> None:
        from sustech_rag.utils.runtime import ensure_gguf_model, ensure_llama_cpp_binary

        if not isinstance(config.llm, LlamaCppConfig):
            raise TypeError("LlamaCppLauncher requires a llama_cpp configuration.")
        local = config.llm
        self.binary = ensure_llama_cpp_binary()
        self.model_path = ensure_gguf_model(local.model_path)
        self._endpoint = client.endpoint
        self._device_mode = local.device_mode
        self._device_name = local.device_name
        self._gpu_layers = local.gpu_layers
        self._threads = local.threads
        self._threads_batch = local.threads_batch
        self._reasoning = local.reasoning
        self._n_ctx = local.n_ctx
        self._extra_args = local.extra_args
        self._proc: subprocess.Popen | None = None
        self._client = client

    def start(self) -> None:
        self._start_process()
        print("[sustech-rag] warm-up inference ...", flush=True)
        result = self._client.generate([{"role": "user", "content": "Hello."}])
        print(f"[sustech-rag] model hot & ready (warm-up: {len(result)} chars)", flush=True)

    def shutdown(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        self._proc = None

    def verify(self) -> tuple[bool, str]:
        if not Path(self.binary).exists():
            return False, f"llama-server binary not found: {self.binary}"
        if not self.model_path:
            return False, "llama.cpp model path is not configured"
        if not Path(self.model_path).exists():
            return False, f"GGUF model not found: {self.model_path}"
        return True, "ok"

    def _start_process(self) -> None:
        cmd = [self.binary]
        cmd.extend(self._build_runtime_args())
        cmd.extend([
            "-m", self.model_path,
            "--host", self._endpoint.host,
            "--port", str(self._endpoint.port),
            "-c", str(self._n_ctx),
        ])
        cmd.extend(self._extra_args)
        print(
            f"[sustech-rag] starting llama-server on {self._endpoint.host}:{self._endpoint.port} ...",
            flush=True,
        )
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: float = 120) -> None:
        deadline = time.time() + timeout
        attempts = 0
        last_error: str | None = None
        while time.time() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(
                    "llama-server exited unexpectedly. "
                    "Check the process output above for diagnostics."
                )
            try:
                if self._probe_ready():
                    print("[sustech-rag] llama-server is ready.", flush=True)
                    return
            except httpx.RequestError as exc:
                last_error = str(exc)
            attempts += 1
            time.sleep(0.5)
        msg = f"llama-server did not become ready within {timeout}s (polled {attempts} times"
        if last_error:
            msg += f", last error: {last_error}"
        msg += ")"
        raise RuntimeError(msg)

    def _probe_ready(self) -> bool:
        resp = httpx.get(f"{self._endpoint.base_url}/health", timeout=2)
        return resp.status_code == 200

    def _build_runtime_args(self) -> list[str]:
        args: list[str] = []
        device_arg = self._resolve_device_arg()
        if device_arg is not None:
            args.extend(["--device", device_arg])
        if self._gpu_layers:
            args.extend(["-ngl", str(self._gpu_layers)])
        if self._threads > 0:
            args.extend(["-t", str(self._threads)])
        if self._threads_batch > 0:
            args.extend(["-tb", str(self._threads_batch)])
        if self._reasoning:
            args.extend(["--reasoning", self._reasoning])
        return args

    _KNOWN_DEVICE_MODES = {
        "", "auto", "cpu", "custom",
        "metal", "gpu", "cuda", "vulkan", "sycl", "kompute", "opencl",
    }

    def _resolve_device_arg(self) -> str | None:
        mode = self._device_mode.lower().strip()
        if mode in {"", "auto"}:
            return None
        if mode == "cpu":
            return "none"
        if mode == "metal":
            return None
        if mode == "custom":
            if not self._device_name:
                raise ValueError("llama.cpp device_mode=custom requires device_name.")
            return self._device_name
        if mode in self._KNOWN_DEVICE_MODES:
            return self._device_name or mode
        raise ValueError(
            f"Unknown device_mode: {self._device_mode!r}. "
            f"Expected one of: {', '.join(sorted(self._KNOWN_DEVICE_MODES))}."
        )
