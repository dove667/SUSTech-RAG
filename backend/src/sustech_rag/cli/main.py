from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sustech_rag.config.loader import load_config

app = typer.Typer(no_args_is_help=True, help="SUSTech campus knowledge base RAG CLI.")


@app.command()
def crawl(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    """
    执行站点抓取流程，并输出抓取到的原始文档数量。
    输入参数：
        config：YAML 配置文件路径，用于加载抓取相关配置。

    输出参数：
        None：无返回值，结果通过终端输出。
    """
    from sustech_rag.pipeline.builders import crawl_documents

    app_config = load_config(config)
    docs = crawl_documents(app_config)
    typer.echo(f"Crawled {len(docs)} raw documents.")


@app.command()
def preprocess(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    """
    执行文档预处理与分块流程，并输出处理结果统计。
    输入参数：
        config：YAML 配置文件路径，用于加载预处理相关配置。
    输出参数：
        None：无返回值，结果通过终端输出。
    """
    from sustech_rag.pipeline.builders import build_chunks, preprocess_documents

    app_config = load_config(config)
    docs = preprocess_documents(app_config)
    chunks = build_chunks(app_config)
    typer.echo(f"Preprocessed {len(docs)} documents into {len(chunks)} chunks.")


@app.command()
def index(
    config: str = typer.Option(None, help="Path to YAML config file."),
    rebuild: bool = typer.Option(
        False,
        "--rebuild",
        help="Delete existing collection before building index.",
    ),
) -> None:
    """
    构建向量索引，并输出索引持久化目录信息。
    输入参数：
        config：YAML 配置文件路径，用于加载索引相关配置。
        rebuild：是否重建索引，若为 True 则先删除已有 collection。
    输出参数：
        None：无返回值，结果通过终端输出。
    """
    from sustech_rag.indexing.vector_index import build_vector_index

    app_config = load_config(config)
    _ = build_vector_index(app_config, rebuild=rebuild)
    typer.echo(f"Indexed chunks into {app_config.vector_store.persist_dir}.")


@app.command()
def query(
    question: str,
    config: str = typer.Option(None, help="Path to YAML config file."),
) -> None:
    """
    执行一次命令行 RAG 问答，并输出模型回答。

    这个命令用于端到端检查：会临时启动 llama-server，完成一次检索、
    rerank 和生成后立即关闭。连续对话或前端联调请使用 serve，让
    llama-server 常驻内存，避免每次提问都重新加载模型。

    输入参数：
        question：用户输入的问题文本。
        config：YAML 配置文件路径，用于加载问答相关配置。
    输出参数：
        None：无返回值，答案通过终端输出。
    """
    from sustech_rag.pipeline.rag_service import RagService

    app_config = load_config(config)
    service = RagService(app_config)
    # query 是一次性命令行检查入口；llama-server 只在本次回答期间存活。
    service.llm.start()
    try:
        typer.echo(service.answer(question))
    finally:
        service.llm.shutdown()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host."),
    port: int = typer.Option(8001, help="Bind port."),
    config: str = typer.Option(None, help="Path to YAML config file."),
) -> None:
    """
    启动与前端 WebUI 对接的 HTTP API（FastAPI + SSE）。
    默认与仓库内前端 Vite 代理一致：后端 8001，前端将 /api 转发到此服务。
    """
    from sustech_rag.api.app import run_dev_server

    app_config = load_config(config)
    run_dev_server(app_config, host=host, port=port)


@app.command()
def paths(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    """
    输出项目相关数据目录与配置目录路径。
    输入参数：
        config：YAML 配置文件路径，用于加载路径相关配置。
    输出参数：
        None：无返回值，路径通过终端逐行输出。
    """
    app_config = load_config(config)
    for path in [
        app_config.project.data_dir,
        app_config.vector_store.persist_dir,
        Path("configs").resolve(),
    ]:
        typer.echo(str(path))


@app.command("download-model")
def download_model() -> None:
    """下载 embedding、reranker 和 GGUF 模型到默认 data/models 目录。"""
    from sustech_rag.utils.download_model import download_models

    download_models()


@app.command("download-llama")
def download_llama(
    install_dir: Annotated[
        Path | None,
        typer.Option(help="Directory for llama.cpp binaries. Add it to PATH if needed."),
    ] = None,
) -> None:
    """安装当前平台匹配的 llama.cpp llama-server。"""
    from sustech_rag.utils.download_llama import (
        default_llama_install_dir,
        install_llama_cpp,
        path_contains,
    )

    target_dir = (install_dir or default_llama_install_dir()).expanduser()
    install_llama_cpp(target_dir)
    if path_contains(target_dir):
        return

    typer.echo()
    typer.echo(f"Add this directory to PATH before running the backend: {target_dir}")
