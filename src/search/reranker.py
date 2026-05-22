"""Rerank — 硅基流动 API 优先，本地 CrossEncoder 回退"""

import logging
import asyncio
from typing import List

from src.search.schemas import RankedChunk

logger = logging.getLogger(__name__)


async def rerank(
    query: str,
    chunks: List[RankedChunk],
    top_k: int = 5,
) -> List[RankedChunk]:
    """使用硅基流动 /v1/rerank API 重排序（或回退本地模型）"""
    if not chunks:
        return []

    try:
        from src.rag.reranker import create_reranker
        loop = asyncio.get_event_loop()
        reranker = await loop.run_in_executor(None, create_reranker)
    except Exception as e:
        logger.warning("[Rerank] 创建 reranker 失败: %s", e)
        return chunks[:top_k]

    # 转换为 LangChain Document
    from langchain_core.documents import Document
    docs = [Document(page_content=c.text, metadata={"source_url": c.source_url}) for c in chunks]

    try:
        ranked_docs = await loop.run_in_executor(
            None, lambda: reranker.rerank(query, docs, top_k=top_k),
        )
    except Exception as e:
        logger.warning("[Rerank] 失败: %s", e)
        return chunks[:top_k]

    result = []
    seen_urls = set()
    for rank, doc in enumerate(ranked_docs, 1):
        url = doc.metadata.get("source_url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        score = float(doc.metadata.get("rerank_score", 0.0))
        # 匹配原始 chunk
        for c in chunks:
            if c.source_url == url:
                result.append(RankedChunk(
                    chunk_id=c.chunk_id, text=doc.page_content,
                    source_url=c.source_url, source_title=c.source_title,
                    chunk_index=c.chunk_index, relevance_score=score, rank=rank,
                ))
                break

    logger.info("[Rerank] %d chunks → top_%d (best=%.4f)", len(chunks), len(result),
                result[0].relevance_score if result else 0.0)
    return result
