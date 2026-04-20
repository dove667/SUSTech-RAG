from __future__ import annotations

import chromadb
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from sustech_rag.config.models import AppConfig
from sustech_rag.retrieval.reranker import BGECrossEncoderReranker, RetrievedChunk
from sustech_rag.utils.runtime import prepare_model_cache


class RetrievalEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        prepare_model_cache(config.project.data_dir)
        model_ref = config.embedding.local_path or config.embedding.model_name
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=model_ref,
            cache_folder=str(config.project.data_dir / "cache" / "huggingface"),
        )
        client = chromadb.PersistentClient(path=str(config.vector_store.persist_dir))
        collection = client.get_or_create_collection(config.vector_store.collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        self.index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        reranker_ref = config.retrieval.reranker_local_path or config.retrieval.reranker_model
        self.reranker = BGECrossEncoderReranker(reranker_ref)

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        retriever = self.index.as_retriever(similarity_top_k=self.config.retrieval.similarity_top_k)
        nodes = retriever.retrieve(query)
        rough = [
            RetrievedChunk(text=node.text, score=float(node.score or 0.0), metadata=node.metadata)
            for node in nodes
        ]
        return self.reranker.rerank(query, rough, top_n=self.config.retrieval.rerank_top_n)
