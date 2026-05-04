"""Install llama.cpp's llama-server for the current platform."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from sustech_rag.utils.platform import default_llama_binary_name

_LLAMA_RELEASE_API = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"


def default_llama_install_dir() -> Path:
    if platform.system().lower() == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "sustech-rag" / "bin"
    return Path.home() / ".local" / "bin"


def _asset_platform_terms() -> list[str]:
    system = platform.system().lower()
    if system == "windows":
        return ["win", "windows"]
    if system == "darwin":
        return ["mac", "macos", "darwin"]
    if system == "linux":
        return ["linux", "ubuntu"]
    return [system]


def _asset_arch_terms() -> tuple[list[str], list[str]]:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return ["arm64", "aarch64"], ["x64", "x86_64", "amd64"]
    if machine in {"x86_64", "amd64"}:
        return ["x64", "x86_64", "amd64"], ["arm64", "aarch64"]
    return [machine], []


def _score_asset(name: str) -> int | None:
    lower_name = name.lower()
    if not lower_name.endswith(".zip"):
        return None
    if not any(term in lower_name for term in _asset_platform_terms()):
        return None

    arch_terms, rejected_arch_terms = _asset_arch_terms()
    if any(term in lower_name for term in rejected_arch_terms):
        return None

    score = 10
    if any(term in lower_name for term in arch_terms):
        score += 20
    if "server" in lower_name:
        score += 4
    if "vulkan" in lower_name and platform.system().lower() != "darwin":
        score += 3
    if "cudart" in lower_name or "cuda" in lower_name:
        score -= 8
    return score


def install_llama_cpp(install_dir: Path) -> Path:
    binary_name = default_llama_binary_name()
    existing = shutil.which(binary_name)
    if existing:
        print("llama-server already on PATH:", existing)
        return Path(existing)

    print("Fetching latest llama.cpp release metadata ...")
    request = Request(
        _LLAMA_RELEASE_API,
        headers={"User-Agent": "sustech-rag", "Accept": "application/vnd.github+json"},
    )
    with urlopen(request, timeout=30) as response:
        release = json.loads(response.read().decode("utf-8"))

    scored_assets = [
        (score, asset)
        for asset in release.get("assets", [])
        if (score := _score_asset(asset.get("name", ""))) is not None
    ]
    if not scored_assets:
        raise SystemExit(
            "No compatible llama.cpp release asset found for "
            f"{platform.system()} {platform.machine()}."
        )

    _, asset = max(scored_assets, key=lambda item: item[0])
    asset_name = asset["name"]
    print(f"Installing llama.cpp {release['tag_name']} asset {asset_name} ->", install_dir)
    download_request = Request(asset["browser_download_url"], headers={"User-Agent": "sustech-rag"})
    with urlopen(download_request, timeout=600) as response:
        archive_path = install_dir / asset_name
        install_dir.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(response.read())

    installed_binary: Path | None = None
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = install_dir / Path(member.filename).name
            if not target.name:
                continue
            with archive.open(member) as source:
                target.write_bytes(source.read())
            if target.name.lower() == binary_name.lower():
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                installed_binary = target
    archive_path.unlink(missing_ok=True)

    if installed_binary is None:
        raise SystemExit(f"{binary_name} was not found in {asset_name}.")

    if not path_contains(install_dir):
        print("Installed llama-server at:", installed_binary)
        print("Add this directory to PATH before running the backend:", install_dir)
    else:
        print("Installed llama-server:", installed_binary)
    return installed_binary


def path_contains(directory: Path) -> bool:
    directory = directory.expanduser().resolve()
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    return any(Path(entry).expanduser().resolve() == directory for entry in path_entries if entry)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=default_llama_install_dir(),
        help="Directory for llama.cpp binaries. Add it to PATH if needed.",
    )
    args = parser.parse_args()
    install_dir = args.install_dir.expanduser()

    install_llama_cpp(install_dir)

    if not path_contains(install_dir):
        print()
        if platform.system().lower() == "windows":
            print(f'Windows PATH example: setx PATH "%PATH%;{install_dir}"')
        else:
            print(f'Unix PATH example: export PATH="{install_dir}:$PATH"')
        print("The backend will only find llama-server after that directory is on PATH.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
