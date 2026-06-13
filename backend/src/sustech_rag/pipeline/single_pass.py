"""
Single-Pass RAG Controller — 用单次 LLM 生成完成路由、检索分析、草稿、自检、输出。

XML 标签协议
============

Step 1: 路由 + 回答（无需检索时一步完成）
----------
需要检索:
  <retrieval_decision>
  <should_retrieve>true</should_retrieve>
  <reason>用户询问南科大招生政策，需要检索相关资料</reason>
  </retrieval_decision>

无需检索:
  <retrieval_decision>
  <should_retrieve>false</should_retrieve>
  <reason>用户询问天气，与南科大无关</reason>
  </retrieval_decision>
  <output>您的问题超出了南科大校园知识库的服务范围...</output>

Step 2-4: 检索分析 → 草稿 → 自检 → 输出
----------
<relevance_analysis>
（逐份分析候选文档相关性，从中能获取什么信息）
（重复文档中的关键字、关键短语）
关键信息：
- 文档1关键字：招生章程, 本科, 2025年, 录取标准
- 文档3关键字：书院制, 通识教育, 创新创业, 导师制
</relevance_analysis>

<draft>
（基于检索上下文的草稿要点）
</draft>

<self_check>
（逐条核验草稿中的事实是否被检索上下文支持）
（每条标注 ✓ 或 ✗）
结论：supported（证据充分） / unsupported（证据不足）
</self_check>

如果 supported:
  <output>最终回答...</output>

如果 unsupported:
  <need_more_retrieval/>
"""

from __future__ import annotations

import re
import threading
from collections.abc import Iterator
from typing import Any

from sustech_rag.llm.base import LLMClient
from sustech_rag.retrieval.reranker import RetrievedChunk


# ---------------------------------------------------------------------------
# XML 解析工具
# ---------------------------------------------------------------------------

def extract_tag(text: str, tag: str) -> str:
    """提取 <tag>...</tag> 之间的内容（保留内部 XML）。"""
    pattern = rf"<{tag}\b[^>]*>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def has_self_closing_tag(text: str, tag: str) -> bool:
    """检查是否存在自闭合标签 <tag/>。"""
    return bool(re.search(rf"<{tag}\s*/>", text))


def _has_tag(text: str, tag: str) -> bool:
    """检查是否存在 <tag>...</tag> 或 <tag/>。"""
    return bool(re.search(rf"<{tag}\b", text))


def extract_tag_outer(text: str, tag: str) -> str:
    """提取 <tag>...</tag> 整段（含标签）。"""
    pattern = rf"<{tag}\b[^>]*>.*?</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0).strip() if match else ""


# ---------------------------------------------------------------------------
# 解析结构
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass
class RouterResult:
    should_retrieve: bool = True
    reason: str = ""
    output: str = ""  # should_retrieve=false 时的直接回答


@dataclass
class RetrievalResult:
    relevance_analysis: str = ""
    draft: str = ""
    self_check: str = ""
    output: str = ""
    need_more: bool = False
    is_supported: bool = False
    raw_text: str = ""


# ---------------------------------------------------------------------------
# 提示词
# ---------------------------------------------------------------------------

_ROUTER_SYSTEM = """你是南方科技大学校园知识库问答系统的请求路由器兼回答助手。

你的任务：
1. 判断用户请求是否需要检索南科大知识库
2. 如果不需要检索，直接给出回答并礼貌引导用户提问南科大相关问题
3. 如果需要检索，只输出判断结论，不要输出回答

你必须严格按以下 XML 格式输出：

不需要检索时：
<retrieval_decision>
<should_retrieve>false</should_retrieve>
<reason>（简短说明为何不需要检索）</reason>
</retrieval_decision>
<output>
（1-3句话，礼貌拒绝并引导用户提问南科大相关问题，使用中文）
</output>

需要检索时：
<retrieval_decision>
<should_retrieve>true</should_retrieve>
<reason>（简短说明为何需要检索）</reason>
</retrieval_decision>

规则：
- 闲聊、天气、计算、翻译、代码等与南科大事实信息无关的请求 → should_retrieve=false
- 需要南科大相关事实、政策、机构、课程、活动、人物、地点、时间等 → should_retrieve=true
- 不要输出任何 XML 标签之外的文字"""

_RETRIEVAL_SYSTEM = """你是南方科技大学的校园知识库问答助手。
你需要基于检索上下文完成以下任务，并用严格的 XML 格式输出。

检索上下文可能包含不相关的噪音文档。你必须：
1. 先逐份分析哪份候选文档与用户问题相关，从中能获取什么信息
2. 提取并重复文档中的关键字和关键短语
3. 基于相关文档拟一个简洁回答草稿
4. 逐条核验草稿中的事实是否都能在检索上下文中找到明确依据
5. 如果证据充分，输出最终回答；如果证据不足，标记需要更多检索

=== 严格输出格式 ===

<relevance_analysis>
文档1：[与问题的关联性判断]，[能从中获取的具体信息]
文档2：...
关键信息：
- 文档X关键字：关键词1, 关键词2, 关键词3
- 文档Y关键字：关键词1, 关键词2
</relevance_analysis>

<draft>
（基于检索上下文，简洁地列出回答要点，每个要点一行）
- 要点1
- 要点2
</draft>

<self_check>
逐条核验：
- 草稿中的"要点1"→ 在文档X中有明确记载 ✓
- 草稿中的"要点2"→ 在文档Y中有明确记载 ✓
（如有不实之处标注 ✗）
结论：supported（所有要点均有据可查）/ unsupported（某要点缺乏依据）
</self_check>

如果 supported：
<output>
（基于检索上下文，用中文给出完整、准确、简洁的回答。引用信息来源标题）
</output>

如果 unsupported：
<need_more_retrieval/>

=== 核心规则 ===
- 严格遵守 XML 格式，不要遗漏任何标签
- <self_check> 中必须逐条核验，不能笼统说"都有依据"
- <output> 中如果引用具体事实，确保在 <relevance_analysis> 或 <draft> 中有对应来源
- 禁止编造检索上下文中没有的事实、数字、名称"""


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class SinglePassController:
    """单次生成多任务 RAG 控制器。"""

    MAX_RETRIES = 1  # 格式错误时最多重试 1 次

    def __init__(self, llm: LLMClient, max_rounds: int = 2) -> None:
        self._llm = llm
        self.max_rounds = max(1, max_rounds)

    # ------------------------------------------------------------------
    # 容错生成：格式错误时追加纠正提示并重试
    # ------------------------------------------------------------------

    def _generate_with_xml_retry(
        self,
        messages: list[dict],
        required_tags: list[str],
        required_any_tag: list[str] | None = None,
    ) -> str:
        """生成并校验 XML 格式；格式错误时追加纠正提示重试一次。

        Args:
            messages: 初始消息列表（会被原地修改以追加纠正信息）。
            required_tags: 必须全部出现的 XML 标签名。
            required_any_tag: 至少出现其中之一的标签名。

        Returns:
            模型输出的原始文本。
        """
        text = self._llm.generate(messages)

        for attempt in range(self.MAX_RETRIES + 1):
            missing = [t for t in required_tags if not _has_tag(text, t)]
            any_missing = (
                required_any_tag is not None
                and not any(_has_tag(text, t) for t in required_any_tag)
            )
            if not missing and not any_missing:
                return text  # 格式正确

            if attempt >= self.MAX_RETRIES:
                # 最后一次重试仍失败 → 返回原始文本（调用方做最终兜底）
                return text

            # 构造纠正提示
            correction = "\n\n【格式错误】你的上一次输出缺少以下必需的 XML 标签：\n"
            for tag in missing:
                correction += f"  - <{tag}>...</{tag}>\n"
            if any_missing:
                correction += (
                    f"  并且必须包含以下标签之一：{' / '.join(required_any_tag)}\n"
                )
            correction += "\n请严格按照要求的 XML 格式重新输出完整内容。"
            messages.append({"role": "user", "content": correction})
            text = self._llm.generate(messages)

        return text

    # ------------------------------------------------------------------
    # Step 1: 路由 + 可选直接回答
    # ------------------------------------------------------------------

    def build_router_messages(
        self, query: str, history: list[dict]
    ) -> list[dict]:
        """构建路由判断的消息列表。"""
        history_text = _format_history(history)
        user_prompt = (
            f"对话历史：\n{history_text}\n\n用户问题：{query}"
        )
        return [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    def parse_router_output(self, text: str) -> RouterResult:
        """解析路由判断的 XML 输出。"""
        decision_block = extract_tag_outer(text, "retrieval_decision")
        should_retrieve = "true" in extract_tag(decision_block, "should_retrieve").lower()
        reason = extract_tag(decision_block, "reason")
        output = extract_tag(text, "output")
        return RouterResult(
            should_retrieve=should_retrieve,
            reason=reason,
            output=output,
        )

    # ------------------------------------------------------------------
    # Step 2-4: 检索分析 → 草稿 → 自检 → 输出
    # ------------------------------------------------------------------

    def build_retrieval_messages(
        self, query: str, chunks: list[RetrievedChunk], history: list[dict]
    ) -> list[dict]:
        """构建检索分析的消息列表。"""
        context = "\n\n".join(
            f"[{idx + 1}] {chunk.metadata.get('title', 'Untitled')}\n{chunk.text}"
            for idx, chunk in enumerate(chunks)
        )
        # 合并对话历史
        history_entries = []
        for m in history[-6:]:
            role = str(m.get("role") or "user")
            content = str(m.get("content") or "").strip()
            if content:
                history_entries.append(f"{role}: {content}")
        history_text = "\n".join(history_entries) if history_entries else "<无历史>"

        user_prompt = (
            f"对话历史：\n{history_text}\n\n"
            f"用户问题：{query}\n\n"
            f"检索上下文：\n{context}"
        )
        return [
            {"role": "system", "content": _RETRIEVAL_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    def parse_retrieval_output(self, text: str) -> RetrievalResult:
        """解析检索分析的 XML 输出。"""
        relevance_analysis = extract_tag(text, "relevance_analysis")
        draft = extract_tag(text, "draft")
        self_check = extract_tag(text, "self_check")
        output = extract_tag(text, "output")
        need_more = has_self_closing_tag(text, "need_more_retrieval")
        # 判断 supported：self_check 中包含 "supported" 且不在否定语境
        is_supported = (
            "supported" in self_check.lower()
            and "no" not in self_check.lower()
            and not need_more
        )
        return RetrievalResult(
            relevance_analysis=relevance_analysis,
            draft=draft,
            self_check=self_check,
            output=output,
            need_more=need_more,
            is_supported=is_supported,
            raw_text=text,
        )


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _format_history(history: list[dict]) -> str:
    entries = []
    for item in history[-6:]:
        role = str(item.get("role") or "user")
        content = str(item.get("content") or "").strip()
        if content:
            entries.append(f"{role}: {content}")
    return "\n".join(entries) if entries else "<无历史>"
