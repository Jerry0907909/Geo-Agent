"""Embedding 相似度召回 — 复用现有 embedding provider"""

import logging
import asyncio
from typing import List

import numpy as np

from src.search.schemas import ExtractedChunk, RankedChunk

logger = logging.getLogger(__name__)


async def retrieve(
    query: str,
    chunks: List[ExtractedChunk],
    top_k: int = 10,
    embedding_provider=None,
) -> List[RankedChunk]:
    """使用 embedding 对候选 chunk 进行相似度召回"""
    if not chunks:
        return []

    if embedding_provider is None:
        from src.core.embedding_provider import create_embedding_provider
        embedding_provider = create_embedding_provider(use_cache=False)

    texts = [c.text for c in chunks]

    try:
        loop = asyncio.get_event_loop()
        query_emb = await loop.run_in_executor(
            None, lambda: embedding_provider.embed_query(query)
        )
        chunk_embs = await loop.run_in_executor(
            None, lambda: embedding_provider.embed_documents(texts)
        )
    except Exception as e:
        logger.warning("[Retrieve] embedding 失败: %s，使用原始顺序", e)
        return _fallback_ranking(chunks, top_k)

    query_vec = np.array(query_emb, dtype=np.float32)
    scores = []
    for i, emb in enumerate(chunk_embs):
        vec = np.array(emb, dtype=np.float32)
        sim = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-8))
        scores.append((i, sim))

    scores.sort(key=lambda x: x[1], reverse=True)

    ranked = []
    for rank, (idx, sim) in enumerate(scores[:top_k], 1):
        c = chunks[idx]
        ranked.append(RankedChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            source_url=c.source_url,
            source_title=c.source_title,
            chunk_index=c.chunk_index,
            relevance_score=round(sim, 4),
            rank=rank,
        ))

    logger.info("[Retrieve] %d → top_%d (best score=%.4f)", len(chunks), len(ranked),
                ranked[0].relevance_score if ranked else 0.0)
    return ranked


def _fallback_ranking(chunks: List[ExtractedChunk], top_k: int) -> List[RankedChunk]:
    ranked = []
    for i, c in enumerate(chunks[:top_k], 1):
        ranked.append(RankedChunk(
            chunk_id=c.chunk_id, text=c.text,
            source_url=c.source_url, source_title=c.source_title,
            chunk_index=c.chunk_index, relevance_score=0.5, rank=i,
        ))
    return ranked
