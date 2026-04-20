from __future__ import annotations

from pathlib import Path

import typer

from sustech_rag.config.loader import load_config

app = typer.Typer(no_args_is_help=True, help="SUSTech campus knowledge base RAG CLI.")


@app.command()
def crawl(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    from sustech_rag.pipeline.builders import crawl_documents

    app_config = load_config(config)
    docs = crawl_documents(app_config)
    typer.echo(f"Crawled {len(docs)} raw documents.")


@app.command()
def preprocess(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    from sustech_rag.pipeline.builders import build_chunks, preprocess_documents

    app_config = load_config(config)
    docs = preprocess_documents(app_config)
    chunks = build_chunks(app_config)
    typer.echo(f"Preprocessed {len(docs)} documents into {len(chunks)} chunks.")


@app.command()
def index(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    from sustech_rag.indexing.vector_index import build_vector_index

    app_config = load_config(config)
    _ = build_vector_index(app_config)
    typer.echo(f"Indexed chunks into {app_config.vector_store.persist_dir}.")


@app.command()
def query(
    question: str,
    config: str = typer.Option(None, help="Path to YAML config file."),
) -> None:
    from sustech_rag.pipeline.rag_service import RagService

    app_config = load_config(config)
    service = RagService(app_config)
    typer.echo(service.answer(question))


@app.command()
def paths(config: str = typer.Option(None, help="Path to YAML config file.")) -> None:
    app_config = load_config(config)
    for path in [
        app_config.project.data_dir,
        app_config.vector_store.persist_dir,
        Path("configs").resolve(),
    ]:
        typer.echo(str(path))
