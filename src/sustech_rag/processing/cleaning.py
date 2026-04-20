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


def repeated_line_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 1.0
    counts = Counter(lines)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / max(len(lines), 1)


def is_high_quality(doc: RawDocument, config: ProcessingConfig) -> bool:
    if len(doc.text) < config.min_text_length:
        return False
    if repeated_line_ratio(doc.text) > config.max_repeated_line_ratio:
        return False
    return True
