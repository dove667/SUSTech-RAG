from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from sustech_rag.config.models import AppConfig, VLLMConfig
from sustech_rag.llm.base import OpenAICompatibleEndpoint


class VLLMClient:
    """OpenAI-compatible vLLM client; does not manage the server process."""

    def __init__(self, config: AppConfig) -> None:
        if not isinstance(config.llm, VLLMConfig):
            raise TypeError("VLLMClient requires a vllm configuration.")
        self._endpoint = OpenAICompatibleEndpoint(
            model_path=config.llm.local_path,
            host="127.0.0.1",
            port=config.llm.server_port,
            served_model_name=config.llm.served_model_name,
            api_key=config.llm.api_key,
        )
        self._temperature = config.llm.temperature
        self._max_tokens = config.llm.max_tokens
        self._stop = config.llm.stop

    @property
    def endpoint(self) -> OpenAICompatibleEndpoint:
        return self._endpoint

    def generate(self, messages: list[dict]) -> str:
        payload: dict[str, object] = {
            "model": self._endpoint.served_model_name,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        if self._stop:
            payload["stop"] = self._stop
        try:
            resp = httpx.post(
                f"{self._endpoint.base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0].get("message", {})
            return (message.get("content") or "").strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"vLLM request failed: {exc}") from exc

    def generate_stream(
        self,
        messages: list[dict],
        cancel_event: threading.Event | None = None,
    ) -> Iterator[tuple[str, str]]:
        payload: dict[str, object] = {
            "model": self._endpoint.served_model_name,
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
                f"{self._endpoint.base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        think = (
                            delta.get("reasoning_content")
                            or delta.get("reasoning")
                            or delta.get("reasoning_text")
                            or ""
                        )
                        text = delta.get("content", "")
                        if think:
                            yield ("think", think)
                        if text:
                            yield ("content", text)
                    except json.JSONDecodeError:
                        printable = data_str[:120]
                        print(
                            f"[sustech-rag] skipped malformed vLLM SSE JSON: {printable}",
                            flush=True,
                        )
                        continue
        except httpx.HTTPError as exc:
            raise RuntimeError(f"vLLM stream request failed: {exc}") from exc

    def _auth_headers(self) -> dict[str, str]:
        if not self._endpoint.api_key:
            return {}
        return {"Authorization": f"Bearer {self._endpoint.api_key}"}


class VLLMLauncher:
    """Launch vLLM in the current Python environment."""

    _ENTRYPOINT = "vllm.entrypoints.openai.api_server"

    def __init__(self, config: AppConfig, client: VLLMClient) -> None:
        if not isinstance(config.llm, VLLMConfig):
            raise TypeError("VLLMLauncher requires a vllm configuration.")
        self._vllm = config.llm
        self._endpoint = client.endpoint
        self._proc: subprocess.Popen | None = None

    def verify(self) -> tuple[bool, str]:
        if not self._endpoint.model_path:
            return False, "vLLM local_path must be configured"
        if importlib.util.find_spec("vllm") is None:
            return False, "vLLM is not installed in the current environment"
        return True, "ok"

    def start(self) -> None:
        self._start_process()

    def shutdown(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=20)
        except Exception:
            proc.kill()
        self._proc = None

    def _start_process(self) -> None:
        cmd = [
            sys.executable,
            "-m",
            self._ENTRYPOINT,
            "--model",
            self._endpoint.model_path,
        ]
        cmd.extend(self._build_runtime_args())
        print(
            f"[sustech-rag] starting vLLM server on {self._endpoint.host}:{self._endpoint.port} "
            f"for model {self._endpoint.served_model_name} ...",
            flush=True,
        )
        self._proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: float = 300) -> None:
        deadline = time.time() + timeout
        attempts = 0
        last_error: str | None = None
        while time.time() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(
                    "vLLM server exited unexpectedly. "
                    "Check the process output above for diagnostics."
                )
            try:
                if self._probe_ready():
                    print("[sustech-rag] vLLM server is ready.", flush=True)
                    return
            except httpx.RequestError as exc:
                last_error = str(exc)
            attempts += 1
            time.sleep(1.0)
        msg = f"vLLM did not become ready within {timeout}s (polled {attempts} times"
        if last_error:
            msg += f", last error: {last_error}"
        msg += ")"
        raise RuntimeError(msg)

    def _probe_ready(self) -> bool:
        health = httpx.get(
            f"{self._endpoint.base_url}/health",
            timeout=2,
            headers=self._auth_headers(),
        )
        if health.status_code == 200:
            return True
        models = httpx.get(
            f"{self._endpoint.base_url}/v1/models",
            timeout=2,
            headers=self._auth_headers(),
        )
        return models.status_code == 200

    def _auth_headers(self) -> dict[str, str]:
        if not self._endpoint.api_key:
            return {}
        return {"Authorization": f"Bearer {self._endpoint.api_key}"}

    def _build_runtime_args(self) -> list[str]:
        cfg = self._vllm
        args = [
            "--host",
            self._endpoint.host,
            "--port",
            str(self._endpoint.port),
            "--dtype",
            cfg.dtype,
            "--gpu-memory-utilization",
            str(cfg.gpu_memory_utilization),
            "--tensor-parallel-size",
            str(cfg.tensor_parallel_size),
            "--pipeline-parallel-size",
            str(cfg.pipeline_parallel_size),
            "--data-parallel-size",
            str(cfg.data_parallel_size),
            "--generation-config",
            cfg.generation_config,
        ]
        if cfg.served_model_name:
            args.extend(["--served-model-name", cfg.served_model_name])
        if cfg.distributed_executor_backend:
            args.extend(
                ["--distributed-executor-backend", cfg.distributed_executor_backend]
            )
        if cfg.max_model_len is not None:
            args.extend(["--max-model-len", str(cfg.max_model_len)])
        if cfg.max_num_seqs is not None:
            args.extend(["--max-num-seqs", str(cfg.max_num_seqs)])
        if cfg.max_num_batched_tokens is not None:
            args.extend(["--max-num-batched-tokens", str(cfg.max_num_batched_tokens)])
        if cfg.reasoning_parser:
            args.extend(["--reasoning-parser", cfg.reasoning_parser])
        if cfg.api_key:
            args.extend(["--api-key", cfg.api_key])
        if cfg.trust_remote_code:
            args.append("--trust-remote-code")
        if cfg.enable_prefix_caching:
            args.append("--enable-prefix-caching")
        if cfg.enable_log_requests:
            args.append("--enable-log-requests")
        if cfg.disable_uvicorn_access_log:
            args.append("--disable-uvicorn-access-log")
        if cfg.max_parallel_loading_workers > 0:
            args.extend(
                ["--max-parallel-loading-workers", str(cfg.max_parallel_loading_workers)]
            )
        args.extend(cfg.extra_args)
        return args
