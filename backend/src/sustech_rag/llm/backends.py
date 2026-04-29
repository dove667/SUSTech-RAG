from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from sustech_rag.config.models import AppConfig
from sustech_rag.utils.platform import default_llama_binary_name, is_windows


class LlamaCppBackend:
    """Persistent llama.cpp backend using llama-server HTTP API.

    Starts *llama-server* once so the GGUF model stays loaded in memory.
    Subsequent ``generate()`` calls use the OpenAI-compatible ``/v1/completions`` endpoint.
    """

    def __init__(self, config: AppConfig) -> None:
        from sustech_rag.utils.ensure_deps import ensure_gguf_model, ensure_llama_cpp_binary

        local = config.llm.local
        raw_binary = self._resolve_binary_path(
            local.binary_path or default_llama_binary_name()
        )
        self.binary = ensure_llama_cpp_binary(raw_binary)
        self.model_path = ensure_gguf_model(
            local.model_path,
            local.hf_repo_id,
            local.hf_filename,
        )
        self._device_mode = local.device_mode
        self._device_name = local.device_name
        self._gpu_layers = local.gpu_layers
        self._threads = local.threads
        self._threads_batch = local.threads_batch
        self._reasoning = local.reasoning
        self._n_ctx = local.n_ctx
        self._temperature = local.temperature
        self._max_tokens = local.max_tokens
        self._stop = local.stop
        self._extra_args = local.extra_args
        self._host = "127.0.0.1"
        self._port = local.server_port
        self._proc: subprocess.Popen | None = None

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Launch llama-server and wait until /health responds, then warm-up."""
        self._start_process()
        print("[sustech-rag] warm-up inference ...", flush=True)
        result = self.generate("Hello.")
        print(f"[sustech-rag] model hot & ready (warm-up: {len(result)} chars)", flush=True)

    def _start_process(self) -> None:
        cmd = [self.binary]
        cmd.extend(self._build_runtime_args())
        cmd.extend([
            "-m", self.model_path,
            "--host", self._host,
            "--port", str(self._port),
            "-c", str(self._n_ctx),
        ])
        cmd.extend(self._extra_args)
        print(f"[sustech-rag] starting llama-server on {self._host}:{self._port} ...", flush=True)
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: float = 120) -> None:
        """Poll /health until the server responds OK."""
        deadline = time.time() + timeout
        attempts = 0
        last_error: str | None = None
        while time.time() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                stderr = b""
                if self._proc.stderr:
                    try:
                        stderr = self._proc.stderr.read()
                    except OSError as exc:
                        stderr = f"(failed to read stderr: {exc})".encode()
                raise RuntimeError(
                    "llama-server exited unexpectedly. stderr: "
                    + stderr.decode("utf-8", errors="replace").strip()
                )
            try:
                resp = httpx.get(
                    f"http://{self._host}:{self._port}/health", timeout=2
                )
                if resp.status_code == 200:
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

    # -- verify -------------------------------------------------------------

    def verify(self) -> tuple[bool, str]:
        if not Path(self.binary).exists():
            return False, f"llama-server binary not found: {self.binary}"
        if not self.model_path:
            return False, "llama.cpp model path is not configured"
        if not Path(self.model_path).exists():
            return False, f"GGUF model not found: {self.model_path}"
        return True, "ok"

    # -- generate -----------------------------------------------------------

    def generate(self, prompt: str) -> str:
        if self._proc is None or self._proc.poll() is not None:
            raise RuntimeError("llama-server is not running")

        payload: dict = {
            "prompt": prompt,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        if self._stop:
            payload["stop"] = self._stop
        try:
            resp = httpx.post(
                f"http://{self._host}:{self._port}/v1/completions",
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["text"].strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"llama-server request failed: {exc}") from exc

    def generate_stream(self, messages: list[dict]) -> Iterator[tuple[str, str]]:
        """Stream via /v1/chat/completions; yields ("think", text) or ("content", text)."""
        if self._proc is None or self._proc.poll() is not None:
            raise RuntimeError("llama-server is not running")

        payload: dict = {
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        if self._stop:
            payload["stop"] = self._stop
        try:
            with httpx.stream(
                "POST",
                f"http://{self._host}:{self._port}/v1/chat/completions",
                json=payload,
                timeout=300,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            think = delta.get("reasoning_content", "")
                            text = delta.get("content", "")
                            if think:
                                yield ("think", think)
                            if text:
                                yield ("content", text)
                    except json.JSONDecodeError:
                        # malformed SSE data line — log a short snippet for diagnostics
                        printable = data_str[:120]
                        print(
                            f"[sustech-rag] skipped malformed SSE JSON: {printable}",
                            flush=True,
                        )
                        continue
        except httpx.HTTPError as exc:
            raise RuntimeError(f"llama-server stream request failed: {exc}") from exc

    # -- helpers ------------------------------------------------------------

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


def build_llm_backend(config: AppConfig) -> LlamaCppBackend:
    """Build the LLM backend (currently only llama.cpp is supported)."""
    return LlamaCppBackend(config)
