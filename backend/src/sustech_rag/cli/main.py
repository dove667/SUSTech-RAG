from __future__ import annotations

from pathlib import Path

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
    rebuild: bool = typer.Option(False, "--rebuild", help="Delete existing collection before building index."),
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
    基于给定问题执行 RAG 问答，并输出模型回答。
    输入参数：
        question：用户输入的问题文本。
        config：YAML 配置文件路径，用于加载问答相关配置。
    输出参数：
        None：无返回值，答案通过终端输出。
    """
    from sustech_rag.pipeline.rag_service import RagService

    app_config = load_config(config)
    service = RagService(app_config)
    typer.echo(service.answer(question))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
    config: str = typer.Option(None, help="Path to YAML config file."),
) -> None:
    """
    启动与前端 WebUI 对接的 HTTP API（FastAPI + SSE）。
    默认与仓库内前端 Vite 代理一致：后端 8000，前端将 /api 转发到此服务。
    """
    from sustech_rag.api.app import run_dev_server

    cfg = str(Path(config).expanduser().resolve()) if config else None
    run_dev_server(host=host, port=port, config_path=cfg)


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
