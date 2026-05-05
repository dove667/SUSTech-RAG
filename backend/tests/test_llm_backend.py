from __future__ import annotations

from sustech_rag.llm.backends import LlamaCppBackend


def _backend_with_runtime_options(device_mode: str, gpu_layers: str = "32") -> LlamaCppBackend:
    backend = object.__new__(LlamaCppBackend)
    backend._device_mode = device_mode
    backend._device_name = ""
    backend._gpu_layers = gpu_layers
    backend._threads = 0
    backend._threads_batch = 0
    backend._reasoning = "off"
    return backend


def test_metal_mode_uses_implicit_llama_cpp_device_selection() -> None:
    backend = _backend_with_runtime_options("metal")

    assert backend._build_runtime_args() == ["-ngl", "32", "--reasoning", "off"]


def test_cpu_mode_disables_device_offload() -> None:
    backend = _backend_with_runtime_options("cpu", gpu_layers="0")

    assert backend._build_runtime_args() == ["--device", "none", "-ngl", "0", "--reasoning", "off"]
