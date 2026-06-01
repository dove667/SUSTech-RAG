from __future__ import annotations

from chromadb.errors import NotFoundError
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from sustech_rag.config.models import AppConfig
from sustech_rag.utils.chroma_client import persistent_client
from sustech_rag.utils.io import read_jsonl
from sustech_rag.utils.runtime import prepare_model_cache, resolve_torch_dtype


def build_vector_index(config: AppConfig, rebuild: bool = False) -> VectorStoreIndex:
    """
    根据配置读取分块数据、初始化向量模型与 Chroma 向量库，并构建向量索引。
    输入参数：
        config: 应用配置对象，包含数据目录、embedding 配置与向量库配置。
        rebuild: 是否重建索引。若为 True，先删除已有 collection 再重新构建。
    输出参数：
        VectorStoreIndex: 构建完成的 LlamaIndex 向量索引对象。
    """
    huggingface_dir = prepare_model_cache(config.project.data_dir)
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
    embedding_kwargs: dict[str, object] = {}
    if config.embedding.device:
        embedding_kwargs["device"] = config.embedding.device
    embedding_dtype = resolve_torch_dtype(config.embedding.dtype)
    if embedding_dtype is not None:
        embedding_kwargs["model_kwargs"] = {"torch_dtype": embedding_dtype}
    embed_model = HuggingFaceEmbedding(
        model_name=model_ref,
        cache_folder=str(huggingface_dir),
        embed_batch_size=config.embedding.batch_size,
        trust_remote_code=True,
        **embedding_kwargs,
    )
    chroma_client = persistent_client(str(config.vector_store.persist_dir))
    if rebuild:
        try:
            chroma_client.delete_collection(config.vector_store.collection_name)
        except (ValueError, NotFoundError):
            # Old/new Chroma versions differ on the missing-collection exception type.
            pass
    collection = chroma_client.get_or_create_collection(config.vector_store.collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
