from __future__ import annotations

from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass(slots=True)
class RetrievedChunk:
    """
    表示检索或重排序流程中的文本片段结果。
    输入参数：无。
    输出参数：RetrievedChunk 实例，包含文本、分数和元数据。
    """

    text: str
    score: float
    metadata: dict


class BGECrossEncoderReranker:
    def __init__(
        self,
        model_name: str,
        device: str = "",
        dtype: object | None = None,
    ) -> None:
        """
        加载 BGE CrossEncoder 模型用于候选片段重排序。
        输入参数：
            model_name：交叉编码器模型名称或本地路径。
        输出参数：无。
        """
        self.model_name = model_name
        automodel_args: dict[str, object] = {}
        if dtype is not None:
            automodel_args["torch_dtype"] = dtype
        self.model = CrossEncoder(
            model_name,
            device=device or None,
            automodel_args=automodel_args or None,
            trust_remote_code=True,
        )

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int | None,
    ) -> list[RetrievedChunk]:
        """
        根据查询语义对候选片段进行重排序并截取前 N 条。
        输入参数：
            query：用户查询文本。
            candidates：待重排序的候选片段列表。
            top_n：返回结果的最大数量；为空时返回完整排序结果。
        输出参数：
            list[RetrievedChunk]：按相关性从高到低排序后的片段列表。
        """
        if not candidates:
            return []
        pairs = [[query, item.text] for item in candidates]
        scores = self.model.predict(pairs)
        ranked = sorted(
            (
                RetrievedChunk(text=item.text, score=float(score), metadata=item.metadata)
                for item, score in zip(candidates, scores, strict=True)
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        if top_n is None:
            return ranked
        return ranked[:top_n]
