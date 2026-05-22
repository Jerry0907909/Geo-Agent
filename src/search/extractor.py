"""正文抽取 — trafilatura 提取网页正文，HTML 清洗"""

import logging
import asyncio
from typing import List

import httpx

from src.search.schemas import RawSearchResult, ExtractedChunk

logger = logging.getLogger(__name__)


async def extract_content(url: str, max_chars: int = 3000) -> str:
    """下载网页并用 trafilatura 抽取正文"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                return ""
            html = resp.text
    except Exception:
        return ""

    try:
        import trafilatura
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )
        if text:
            return text[:max_chars]
    except Exception:
        pass
    return ""


async def extract_batch(results: List[RawSearchResult], max_chars: int = 3000) -> List[ExtractedChunk]:
    """并发提取多个网页正文，生成 chunk 列表"""
    if not results:
        return []

    # 去重 URL
    seen = set()
    unique = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)

    tasks = [extract_content(r.url, max_chars) for r in unique]
    texts = await asyncio.gather(*tasks, return_exceptions=True)

    chunks = []
    chunk_idx = 0
    for r, text in zip(unique, texts):
        if isinstance(text, str) and text.strip():
            # 如果 Tavily 的 content 更长，使用 Tavily 的
            final_text = r.content if len(r.content) > len(text) else text
            chunks.append(ExtractedChunk(
                chunk_id=f"chunk_{chunk_idx}",
                text=final_text[:max_chars],
                source_url=r.url,
                source_title=r.title,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1

    logger.info("[Extract] %d URLs → %d chunks", len(unique), len(chunks))
    return chunks
