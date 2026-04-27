from __future__ import annotations

import re
from collections import Counter

from sustech_rag.config.models import ProcessingConfig
from sustech_rag.pipeline.schemas import RawDocument


def clean_text(text: str, config: ProcessingConfig) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    lines = [line for line in lines if not any(pattern in line for pattern in config.drop_patterns)]
    merged = "\n".join(lines)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def build_effective_text(title: str, text: str, config: ProcessingConfig) -> str:
    clean_title = clean_text(title, config).replace("\n", " ").strip()
    clean_body = clean_text(text, config)
    if not clean_title:
        return clean_body
    if not clean_body:
        return clean_title

    first_line = clean_body.splitlines()[0].strip()
    if _normalize_line(first_line) == _normalize_line(clean_title):
        return clean_body
    return f"{clean_title}\n{clean_body}"


def repeated_line_ratio(text: str) -> float:
    lines = [_normalize_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return 1.0

    repeated_candidates = [line for line in lines if _should_count_repeated_line(line)]
    if not repeated_candidates:
        return 0.0

    counts = Counter(repeated_candidates)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / max(len(repeated_candidates), 1)


def is_high_quality(doc: RawDocument, config: ProcessingConfig) -> bool:
    if len(doc.text) < config.min_text_length:
        return False
    if repeated_line_ratio(doc.text) > config.max_repeated_line_ratio:
        return False
    if not _has_substantive_content(doc.text):
        return False
    return True


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _should_count_repeated_line(line: str) -> bool:
    if len(line) < 8:
        return False
    if re.fullmatch(r"[\d\s\-/:.,()（）年月日]+", line):
        return False
    return True


def _has_substantive_content(text: str) -> bool:
    lines = [_normalize_line(line) for line in text.splitlines() if _normalize_line(line)]
    if not lines:
        return False

    body_lines = lines[1:] if len(lines) > 1 else lines
    return any(_is_substantive_line(line) for line in body_lines)


def _is_substantive_line(line: str) -> bool:
    if len(line) < 8:
        return False
    if re.search(
        r"(电话|邮编|All Rights Reserved|Copyright|ICP备|二维码|扫码登录|再次扫码登录|取消此次登录|刷新页面|^刷新$|login)",
        line,
        re.IGNORECASE,
    ):
        return False
    if len(line) >= 24:
        return True
    return bool(re.search(r"[。！？；;:：]", line))
