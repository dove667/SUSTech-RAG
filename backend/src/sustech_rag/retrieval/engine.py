from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from sustech_rag.config.models import AppConfig
from sustech_rag.retrieval.reranker import BGECrossEncoderReranker, RetrievedChunk
from sustech_rag.retrieval.sparse_search import BM25Searcher
from sustech_rag.utils.chroma_client import persistent_client
from sustech_rag.utils.runtime import prepare_model_cache, resolve_torch_dtype


class RetrievalEngine:
    """初始化向量检索、稀疏检索与重排序引擎，并提供查询检索能力。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        huggingface_dir = prepare_model_cache(config.project.data_dir)
        model_ref = config.embedding.local_path or config.embedding.model_name
        embedding_kwargs: dict[str, object] = {}
        if config.embedding.device:
            embedding_kwargs["device"] = config.embedding.device
        embedding_dtype = resolve_torch_dtype(config.embedding.dtype)
        if embedding_dtype is not None:
            embedding_kwargs["model_kwargs"] = {"torch_dtype": embedding_dtype}
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=model_ref,
            cache_folder=str(huggingface_dir),
            embed_batch_size=config.embedding.batch_size,
            trust_remote_code=True,
            **embedding_kwargs,
        )
        client = persistent_client(str(config.vector_store.persist_dir))
        collection = client.get_or_create_collection(config.vector_store.collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        self.index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        reranker_ref = config.retrieval.reranker_local_path or config.retrieval.reranker_model
        reranker_dtype = resolve_torch_dtype(config.retrieval.reranker_dtype)
        self.reranker = BGECrossEncoderReranker(
            reranker_ref,
            device=config.retrieval.reranker_device,
            dtype=reranker_dtype,
        )

        self._sparse = None
        if config.retrieval.sparse_enabled:
            chunks_path = str(config.project.data_dir / "interim" / "chunks.jsonl")
            self._sparse = BM25Searcher(
                chunks_path=chunks_path,
                top_k=config.retrieval.sparse_top_k,
            )

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """先并行执行向量召回与 BM25 稀疏召回，RRF 融合后再重排序。"""
        if self._sparse is None:
            return self._dense_retrieve_and_rerank(query)

        with ThreadPoolExecutor(max_workers=2) as pool:
            dense_fut = pool.submit(self._dense_retrieve, query)
            sparse_fut = pool.submit(self._sparse_retrieve, query)
            dense = dense_fut.result()
            sparse = sparse_fut.result()

        fused = self._rrf_fusion(dense, sparse)
        return self.reranker.rerank(query, fused, top_n=self.config.retrieval.rerank_top_n)

    def _dense_retrieve(self, query: str) -> list[RetrievedChunk]:
        """纯向量检索（不经 rerank）。"""
        retriever = self.index.as_retriever(
            similarity_top_k=self.config.retrieval.similarity_top_k
        )
        nodes = retriever.retrieve(query)
        return [
            RetrievedChunk(
                text=node.text,
                score=float(node.score or 0.0),
                metadata=node.metadata,
            )
            for node in nodes
        ]

    def _sparse_retrieve(self, query: str) -> list[RetrievedChunk]:
        """BM25 稀疏检索。"""
        if self._sparse is None:
            return []
        return self._sparse.search(query)

    def _dense_retrieve_and_rerank(self, query: str) -> list[RetrievedChunk]:
        """当稀疏检索关闭时的原始流程：向量检索 + 直接 rerank。"""
        chunks = self._dense_retrieve(query)
        for c in chunks:
            c.metadata["source"] = "dense"
        return self.reranker.rerank(query, chunks, top_n=self.config.retrieval.rerank_top_n)

    @staticmethod
    def _rrf_fusion(
        dense: list[RetrievedChunk],
        sparse: list[RetrievedChunk],
        k: int = 60,
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion：按排名合并稠密与稀疏检索结果。"""
        seen: dict[str, tuple[RetrievedChunk, float, str]] = {}
        for rank, chunk in enumerate(dense):
            seen[chunk.text] = (chunk, 1.0 / (k + rank + 1), "dense")
        for rank, chunk in enumerate(sparse):
            rrf = 1.0 / (k + rank + 1)
            if chunk.text in seen:
                prev_chunk, prev_score, _ = seen[chunk.text]
                seen[chunk.text] = (prev_chunk, prev_score + rrf, "hybrid")
            else:
                seen[chunk.text] = (chunk, rrf, "sparse")
        ranked = sorted(seen.values(), key=lambda x: x[1], reverse=True)
        results: list[RetrievedChunk] = []
        for chunk, score, source in ranked:
            chunk.metadata["source"] = source
            results.append(
                RetrievedChunk(
                    text=chunk.text,
                    score=score,
                    metadata=chunk.metadata,
                )
            )
        return results
