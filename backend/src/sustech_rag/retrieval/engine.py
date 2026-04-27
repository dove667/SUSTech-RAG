from __future__ import annotations

import chromadb
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from backend.src.sustech_rag.config.models import AppConfig
from backend.src.sustech_rag.retrieval.reranker import BGECrossEncoderReranker, RetrievedChunk
from backend.src.sustech_rag.utils.runtime import prepare_model_cache


class RetrievalEngine:
    """
    初始化向量检索与重排序引擎，并提供查询检索能力。
    输入参数：无。
    输出参数：RetrievalEngine 实例，用于执行召回与 rerank。
    """

    def __init__(self, config: AppConfig) -> None:
        """
        根据配置初始化 embedding、向量索引和重排序器。
        输入参数：
            config：应用全局配置，包含数据目录、embedding、向量库和检索参数。
        输出参数：无。
        """
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
        """
        先执行向量召回，再使用重排序器返回最终结果。
        输入参数：
            query：用户查询文本。
        输出参数：s
            list[RetrievedChunk]：按相关性排序后的候选片段列表。
        """
        retriever = self.index.as_retriever(similarity_top_k=self.config.retrieval.similarity_top_k)
        nodes = retriever.retrieve(query)
        rough = [
            RetrievedChunk(text=node.text, score=float(node.score or 0.0), metadata=node.metadata)
            for node in nodes
        ]
        return self.reranker.rerank(query, rough, top_n=self.config.retrieval.rerank_top_n)
