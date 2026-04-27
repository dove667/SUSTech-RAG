from sustech_rag.config.models import ProcessingConfig
from sustech_rag.pipeline.schemas import RawDocument
from sustech_rag.processing.cleaning import (
    build_effective_text,
    clean_text,
    is_high_quality,
    repeated_line_ratio,
)


def test_clean_text_and_quality() -> None:
    config = ProcessingConfig(drop_patterns=["版权所有"], min_text_length=8)
    raw = "测试内容说明。\n\n版权所有 SUSTech\n更多内容补充说明。"
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


def test_build_effective_text_prefixes_title() -> None:
    config = ProcessingConfig(drop_patterns=["版权所有"])
    effective = build_effective_text("选课通知", "请同学们按时完成选课。", config)
    assert effective == "选课通知\n请同学们按时完成选课。"


def test_build_effective_text_avoids_duplicate_title_prefix() -> None:
    config = ProcessingConfig()
    effective = build_effective_text("选课通知", "选课通知\n请同学们按时完成选课。", config)
    assert effective == "选课通知\n请同学们按时完成选课。"


def test_high_quality_uses_title_augmented_text_length() -> None:
    config = ProcessingConfig(min_text_length=16)
    effective = build_effective_text("学生活动报名通知", "请尽快完成报名。", config)
    doc = RawDocument(
        doc_id="2",
        url="https://example.com/notice",
        title="学生活动报名通知",
        content_type="text/html",
        text=effective,
        source_path="notice.html",
    )
    assert is_high_quality(doc, config)


def test_repeated_line_ratio_ignores_short_navigation_labels() -> None:
    text = "\n".join(
        [
            "首页",
            "新闻",
            "首页",
            "新闻",
            "这里是保留的正文内容，介绍奖学金申请安排。",
            "这里是保留的正文内容，介绍奖学金申请安排。",
        ]
    )
    assert repeated_line_ratio(text) == 1.0


def test_repeated_line_ratio_detects_template_noise() -> None:
    text = "\n".join(
        [
            "南方科技大学材料科学与工程系欢迎您访问",
            "通知公告栏目将持续更新最新安排",
            "南方科技大学材料科学与工程系欢迎您访问",
            "通知公告栏目将持续更新最新安排",
        ]
    )
    assert repeated_line_ratio(text) == 1.0


def test_repeated_line_ratio_handles_empty_and_single_line() -> None:
    assert repeated_line_ratio("") == 1.0
    assert repeated_line_ratio("只有一行的正文内容") == 0.0


def test_high_quality_rejects_footer_only_content() -> None:
    config = ProcessingConfig(min_text_length=20)
    doc = RawDocument(
        doc_id="3",
        url="https://example.com/footer",
        title="常用系统",
        content_type="text/html",
        text="常用系统\n广东省深圳市南山区学苑大道1088号\n电话： +86-755-88010114\n邮编： 518055",
        source_path="footer.html",
    )
    assert not is_high_quality(doc, config)
