from sustech_rag.config.models import ProcessingConfig
from sustech_rag.pipeline.schemas import RawDocument
from sustech_rag.processing.cleaning import clean_text, is_high_quality


def test_clean_text_and_quality() -> None:
    config = ProcessingConfig(drop_patterns=["版权所有"], min_text_length=10)
    raw = "测试内容\n\n版权所有 SUSTech\n更多内容"
    cleaned = clean_text(raw, config)
    assert "版权所有" not in cleaned

    doc = RawDocument(
        doc_id="1",
        url="https://example.com",
        title="Example",
        content_type="text/html",
        text=cleaned,
        source_path="page.html",
    )
    assert is_high_quality(doc, config)
