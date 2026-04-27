from backend.src.sustech_rag.pipeline.schemas import RawDocument
from backend.src.sustech_rag.processing.chunking import chunk_document


def _make_doc(text: str, title: str = "示例标题") -> RawDocument:
    return RawDocument(
        doc_id="doc-1",
        url="https://example.com/doc-1",
        title=title,
        content_type="text/html",
        text=text,
        source_path="doc-1.html",
    )


def test_chunk_document_prefers_paragraph_boundaries() -> None:
    first = "第一段介绍学校培养方案和课程安排，帮助同学快速了解培养目标。"
    second = "第二段说明选课流程和时间节点，提醒同学按时完成课程报名。"
    doc = _make_doc(f"{first}\n\n{second}")

    chunks = chunk_document(doc, chunk_size=40, chunk_overlap=10)

    assert len(chunks) == 2
    assert chunks[0].text == first
    assert chunks[1].text == second


def test_chunk_document_merges_short_tail_chunks() -> None:
    first = "第一部分详细介绍校园活动安排与参与方式，帮助同学快速掌握活动要求。"
    second = "补充说明报名截止时间。"
    third = "请及时提交材料。"
    doc = _make_doc(f"{first}\n\n{second}\n\n{third}")

    chunks = chunk_document(doc, chunk_size=90, chunk_overlap=10)

    assert len(chunks) == 1
    assert second in chunks[0].text
    assert third in chunks[0].text


def test_chunk_document_keeps_structured_short_page_as_single_chunk() -> None:
    text = "\n".join(
        [
            "学术讲座通知",
            "时间：2026-05-08 14:00",
            "地点：南科大中心楼 201",
            "主讲：张老师",
            "报名：请扫描海报二维码登记",
        ]
    )
    doc = _make_doc(text, title="学术讲座通知")

    chunks = chunk_document(doc, chunk_size=50, chunk_overlap=10)

    assert len(chunks) == 1
    assert chunks[0].text == text
