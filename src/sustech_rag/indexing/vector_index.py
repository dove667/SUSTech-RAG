from __future__ import annotations

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from sustech_rag.config.models import AppConfig
from sustech_rag.utils.io import read_jsonl
from sustech_rag.utils.runtime import prepare_model_cache


def build_vector_index(config: AppConfig) -> VectorStoreIndex:
    prepare_model_cache(config.project.data_dir)
    chunks = read_jsonl(config.project.data_dir / "interim" / "chunks.jsonl")
    documents = [
        Document(
            text=row["text"],
            doc_id=row["chunk_id"],
            metadata={
                "doc_id": row["doc_id"],
                "title": row["title"],
                "source_url": row["source_url"],
                **row.get("metadata", {}),
            },
        )
        for row in chunks
    ]
    model_ref = config.embedding.local_path or config.embedding.model_name
    embed_model = HuggingFaceEmbedding(
        model_name=model_ref,
        cache_folder=str(config.project.data_dir / "cache" / "huggingface"),
    )
    chroma_client = chromadb.PersistentClient(path=str(config.vector_store.persist_dir))
    collection = chroma_client.get_or_create_collection(config.vector_store.collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
