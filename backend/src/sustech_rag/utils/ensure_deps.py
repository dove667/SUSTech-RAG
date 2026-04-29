"""Auto-install missing native dependencies (llama.cpp binary, GGUF weights)."""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen


def _download_llama_cpp_binary(target_name: str, dest_dir: Path) -> str:
    """Download the latest llama.cpp pre-built binary from GitHub releases and extract it."""
    api_url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    print("[sustech-rag] fetching latest llama.cpp release info...", flush=True)
    req = Request(api_url, headers={"User-Agent": "sustech-rag", "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as resp:
        release = json.loads(resp.read().decode())
    print(f"[sustech-rag] latest release: {release['tag_name']}", flush=True)

    plat = sys.platform
    if plat == "win32":
        asset_hint = "win"
        bin_name = "llama-server.exe"
    elif plat == "darwin":
        asset_hint = "mac"
        bin_name = "llama-server"
    else:
        asset_hint = "ubuntu"
        bin_name = "llama-server"

    def _arch_matches(name: str) -> bool:
        n = name.lower()
        if "arm64" in n or "aarch64" in n:
            return False
        if "x64" not in n and "x86_64" not in n:
            return False
        return True

    asset = None
    # Prefer Vulkan build: wide GPU support, no CUDA runtime dependency.
    for a in release["assets"]:
        name = a["name"].lower()
        if not name.endswith(".zip") or asset_hint not in name:
            continue
        if not _arch_matches(name):
            continue
        if name.startswith("cudart-"):
            continue
        if "vulkan" in name:
            asset = a
            break
    # Fallback: CPU-only x64 build.
    if asset is None:
        for a in release["assets"]:
            name = a["name"].lower()
            if not name.endswith(".zip") or asset_hint not in name:
                continue
            if not _arch_matches(name):
                continue
            if name.startswith("cudart-"):
                continue
            if "cuda" not in name and "vulkan" not in name:
                asset = a
                break
    # Last resort: any x64 archive.
    if asset is None:
        for a in release["assets"]:
            name = a["name"].lower()
            if name.endswith(".zip") and asset_hint in name and _arch_matches(name):
                asset = a
                break
    if asset is None:
        raise RuntimeError(
            f"no pre-built llama.cpp binary found for platform '{plat}'. "
            "please install llama.cpp manually: https://github.com/ggerganov/llama.cpp/releases"
        )

    size_mb = asset["size"] / 1024 / 1024
    print(f"[sustech-rag] downloading {asset['name']} ({size_mb:.1f} MB) ...", flush=True)
    dl_req = Request(asset["browser_download_url"], headers={"User-Agent": "sustech-rag"})
    with urlopen(dl_req, timeout=600) as resp:
        data = resp.read()

    dest_dir.mkdir(parents=True, exist_ok=True)
    found_binary: str | None = None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            member_name = Path(member).name
            # extract llama-server + all bundled DLLs
            if member_name.lower() == bin_name.lower() or member_name.lower().endswith(".dll"):
                target = dest_dir / member_name
                with zf.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                print(f"[sustech-rag]   extracted: {member_name}", flush=True)
                if member_name.lower() == bin_name.lower():
                    _make_executable(target)
                    found_binary = str(target)

    if found_binary is None:
        raise RuntimeError(f"binary '{bin_name}' not found inside the release archive")

    # smoke-test the freshly extracted binary
    try:
        subprocess.run(
            [found_binary, "--version"],
            check=True, capture_output=True, timeout=30,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        _cleanup_dest(dest_dir, bin_name)
        raise RuntimeError(
            f"llama-server binary failed to start (exit code {getattr(exc, 'returncode', '?')}).\n"
            "This usually means a system runtime is missing.\n"
            f"Please install the required runtime or download manually."
        ) from exc

    print(f"[sustech-rag] llama.cpp installed to {dest_dir}", flush=True)
    return found_binary


def _cleanup_dest(dest_dir: Path, base_name: str) -> None:
    target = dest_dir / base_name
    if target.is_file():
        target.unlink(missing_ok=True)


def ensure_llama_cpp_binary(binary_path: str) -> str:
    """Ensure *llama-server* is available.  Checks PATH first, then auto-downloads."""
    dest = Path.home() / ".sustech-rag" / "llama-cpp"
    base_name = os.path.basename(binary_path) or binary_path

    cached = dest / base_name
    if cached.is_file():
        try:
            subprocess.run([str(cached), "--version"], check=True, capture_output=True, timeout=30)
            return str(cached.resolve())
        except (subprocess.CalledProcessError, OSError):
            print("[sustech-rag] cached binary is broken, re-downloading ...", flush=True)
            cached.unlink(missing_ok=True)

    if os.path.isfile(binary_path):
        return binary_path

    resolved = shutil.which(binary_path)
    if resolved:
        print(f"[sustech-rag] llama.cpp binary found on PATH: {resolved}", flush=True)
        return resolved

    print("[sustech-rag] llama.cpp binary not found, starting auto-install ...", flush=True)
    return _download_llama_cpp_binary(binary_path, dest)


def ensure_gguf_model(model_path: str, hf_repo_id: str, hf_filename: str) -> str:
    path = Path(model_path)
    if path.exists():
        return str(path)

    if not hf_repo_id or not hf_filename:
        raise FileNotFoundError(
            f"GGUF model not found: {model_path}\n"
            "Set llm.local.hf_repo_id and llm.local.hf_filename in config to enable auto-download."
        )

    print(f"[sustech-rag] GGUF model not found, downloading {hf_repo_id}/{hf_filename} ...", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download
        downloaded = hf_hub_download(repo_id=hf_repo_id, filename=hf_filename, local_dir=str(path.parent))
        print(f"[sustech-rag] GGUF model downloaded to {downloaded}", flush=True)
        return downloaded
    except ImportError:
        raise RuntimeError("huggingface_hub is required to auto-download models. Run: pip install huggingface_hub")


def _make_executable(path: Path) -> None:
    if platform.system().lower() != "windows":
        path.chmod(path.stat().st_mode | 0o111)
