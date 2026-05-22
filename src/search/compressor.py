"""上下文压缩 — token budget 控制 + 去重"""

import logging
from typing import List

import numpy as np

from src.search.schemas import RankedChunk

logger = logging.getLogger(__name__)

# 基于缓存模型的 token 估算：中文约 1.5 char/token，英文约 4，取保守值
CHARS_PER_TOKEN_ZH = 1.3
CHARS_PER_TOKEN_EN = 3.5
SIM_THRESHOLD = 0.85


def compress(
    chunks: List[RankedChunk],
    max_tokens: int = 8000,
    max_chars_per_chunk: int = 600,
) -> List[RankedChunk]:
    """压缩候选 chunk 至 token budget 内"""
    if not chunks:
        return []

    result = []
    total_tokens = 0
    seen_text_sigs = set()

    for c in chunks:
        text = c.text[:max_chars_per_chunk].strip()
        if not text:
            continue

        # 语义去重
        sig = _text_signature(text)
        if sig in seen_text_sigs:
            continue
        seen_text_sigs.add(sig)

        # 近邻去重
        if result and _is_similar(text, result[-1].text):
            continue

        tokens = _estimate_tokens(text)
        if total_tokens + tokens > max_tokens:
            break

        result.append(RankedChunk(
            chunk_id=c.chunk_id, text=text,
            source_url=c.source_url, source_title=c.source_title,
            chunk_index=c.chunk_index,
            relevance_score=c.relevance_score, rank=len(result) + 1,
        ))
        total_tokens += tokens

    logger.info("[Compress] %d → %d chunks (~%d tokens)", len(chunks), len(result), total_tokens)
    return result


def _estimate_tokens(text: str) -> int:
    import re
    zh_chars = len(re.findall(r'[一-鿿]', text))
    other = len(text) - zh_chars
    return int(zh_chars / CHARS_PER_TOKEN_ZH + other / CHARS_PER_TOKEN_EN)


def _text_signature(text: str) -> str:
    """文本前 80 字符签名用于去重"""
    return text[:80].strip().lower().replace(" ", "")


def _is_similar(text_a: str, text_b: str) -> bool:
    """简单 Jacard 相似度"""
    a = set(text_a[:200])
    b = set(text_b[:200])
    if not a or not b:
        return False
    inter = len(a & b)
    union = len(a | b)
    return (inter / union) > SIM_THRESHOLD
