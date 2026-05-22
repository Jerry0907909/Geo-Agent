"""Lightweight language hints for mixed Chinese/English chat text."""

from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_RE = re.compile(r"[a-zA-Z]")


def is_chinese_text(text: str) -> bool:
    """True when text is predominantly Chinese."""
    if not text or not text.strip():
        return False
    cjk = len(_CJK_RE.findall(text))
    if cjk >= 2:
        return True
    latin = len(_LATIN_RE.findall(text))
    return cjk >= 1 and latin < cjk * 2


def conversation_language(question: str, answer: str) -> str:
    """Return 'zh' or 'en' for follow-up / UI copy based on dialogue content."""
    question = (question or "").strip()
    answer = (answer or "").strip()

    if is_chinese_text(question):
        return "zh"
    if is_chinese_text(answer) and len(question) < 24:
        return "zh"

    sample = f"{question} {answer[:500]}"
    cjk = len(_CJK_RE.findall(sample))
    latin = len(_LATIN_RE.findall(sample))
    if cjk >= 4 and cjk >= latin * 0.2:
        return "zh"
    return "en"
