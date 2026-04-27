from __future__ import annotations

import re
from collections import Counter

from sustech_rag.config.models import ProcessingConfig
from sustech_rag.pipeline.schemas import RawDocument


def clean_text(text: str, config: ProcessingConfig) -> str:
    """
    清理文本中的空行与需丢弃的噪声行，并合并多余空白段落。
    输入参数：
    - text: 待清理的原始文本。
    - config: 文本清理配置，用于提供丢弃模式。
    输出参数：
    - 返回清理后的文本字符串。
    """
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    lines = [line for line in lines if not any(pattern in line for pattern in config.drop_patterns)]
    merged = "\n".join(lines)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def build_effective_text(title: str, text: str, config: ProcessingConfig) -> str:
    """
    将标题与正文合成为有效文本，并避免标题重复出现在正文开头。
    输入参数：
    - title: 文档标题。
    - text: 文档正文。
    - config: 文本清理配置。
    输出参数：
    - 返回合并后的有效文本。
    """
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
    """
    计算文本中重复候选行的占比，用于衡量内容噪声程度。
    输入参数：
    - text: 待分析文本。
    输出参数：
    - 返回重复行占比，范围通常在 0 到 1 之间。
    """
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
    """
    根据长度、重复率与内容有效性判断文档是否为高质量文本。
    输入参数：
    - doc: 待判断的原始文档。
    - config: 质量过滤配置。
    输出参数：
    - 返回布尔值，表示文档是否通过高质量筛选。
    """
    if len(doc.text) < config.min_text_length:
        return False
    if repeated_line_ratio(doc.text) > config.max_repeated_line_ratio:
        return False
    if not _has_substantive_content(doc.text):
        return False
    return True


def _normalize_line(text: str) -> str:
    """
    将单行文本中的连续空白归一化为单个空格并去除首尾空白。
    输入参数：
    - text: 待归一化的单行文本。
    输出参数：
    - 返回归一化后的行文本。
    """
    return re.sub(r"\s+", " ", text).strip()


def _should_count_repeated_line(line: str) -> bool:
    """
    判断某行是否应计入重复行统计。
    输入参数：
    - line: 待判断的文本行。
    输出参数：
    - 返回布尔值，表示该行是否应参与重复率计算。
    """
    if len(line) < 8:
        return False
    if re.fullmatch(r"[\d\s\-/:.,()（）年月日]+", line):
        return False
    return True


def _has_substantive_content(text: str) -> bool:
    """
    判断文本是否包含至少一行实质性内容。
    输入参数：
    - text: 待检查文本。
    输出参数：
    - 返回布尔值，表示文本是否包含有效正文内容。
    """
    lines = [_normalize_line(line) for line in text.splitlines() if _normalize_line(line)]
    if not lines:
        return False

    body_lines = lines[1:] if len(lines) > 1 else lines
    return any(_is_substantive_line(line) for line in body_lines)


def _is_substantive_line(line: str) -> bool:
    """
    判断某一行是否属于实质性正文内容。
    输入参数：
    - line: 待判断的文本行。
    输出参数：
    - 返回布尔值，表示该行是否可视为有效内容。
    """
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
