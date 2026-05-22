"""Deep Search 流水线 — 全异步编排"""

import logging
import time
import asyncio
from typing import AsyncGenerator, List

from src.core.llm_provider import create_llm_provider

from src.search.schemas import (
    DeepSearchRequest,
    DeepSearchEvent,
    RawSearchResult,
    ExtractedChunk,
    RankedChunk,
    CitationRef,
)
from src.search.planner import plan_queries
from src.search.tavily_engine import search, search_multi
from src.search.extractor import extract_batch
from src.search.chunker import chunk_extracted
from src.search.retriever import retrieve as embedding_retrieve
from src.search.reranker import rerank as cross_rerank
from src.search.compressor import compress
from src.search.citation import build_citation_prompt

logger = logging.getLogger(__name__)

# 步骤默认配置
DEFAULT_MAX_SOURCES = 8
DEFAULT_MAX_TOKENS = 8000
PLAN_QUERY_COUNT = 4


async def execute(
    request: DeepSearchRequest,
) -> AsyncGenerator[DeepSearchEvent, None]:
    """执行完整深度搜索流水线（SSE 流式）

    每一步失败不阻塞，降级返回最佳可用结果。
    """
    t0 = time.time()
    question = request.question
    max_sources = request.max_sources or DEFAULT_MAX_SOURCES
    max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS

    # ---- Step 1: Query Planning ----
    yield DeepSearchEvent(type="status", message="正在规划搜索策略...")
    try:
        queries = await plan_queries(question, num_queries=PLAN_QUERY_COUNT)
    except Exception:
        logger.exception("[Pipeline] Planner 失败")
        queries = [question]
    logger.info("[Pipeline] Step 1 完成: %d queries", len(queries))

    # ---- Step 2: Search ----
    yield DeepSearchEvent(type="status", message=f"正在搜索 {len(queries)} 个 query...")
    try:
        raw_results = await search_multi(
            queries,
            max_results_per=5,
            time_range=request.time_range,
        )
    except Exception:
        logger.exception("[Pipeline] Search 失败")
        raw_results = await search(question, max_results=8, time_range=request.time_range)
    logger.info("[Pipeline] Step 2 完成: %d raw results", len(raw_results))

    if not raw_results:
        yield DeepSearchEvent(type="error", message="搜索未返回结果，请稍后重试")
        return

    # ---- Step 3: Extract ----
    yield DeepSearchEvent(type="status", message=f"正在读取 {min(len(raw_results), max_sources)} 个网页...")
    top_raw = raw_results[:max_sources]
    try:
        extracted = await extract_batch(top_raw)
    except Exception:
        logger.exception("[Pipeline] Extract 失败，使用 Tavily content")
        extracted = _raw_to_chunks(top_raw)
    if not extracted:
        extracted = _raw_to_chunks(top_raw)
    logger.info("[Pipeline] Step 3 完成: %d extracted", len(extracted))

    # ---- Step 4: Chunk ----
    chunks = chunk_extracted(extracted, chunk_size=512)
    logger.info("[Pipeline] Step 4 完成: %d chunks", len(chunks))

    # ---- Step 5: Embedding Retrieve ----
    yield DeepSearchEvent(type="status", message="正在语义召回最相关内容...")
    try:
        ranked = await embedding_retrieve(question, chunks, top_k=15)
    except Exception:
        logger.exception("[Pipeline] Retrieve 失败")
        ranked = _fallback_rank(chunks, 15)
    logger.info("[Pipeline] Step 5 完成: %d ranked", len(ranked))

    # ---- Step 6: Rerank ----
    yield DeepSearchEvent(type="status", message="正在重排序...")
    try:
        reranked = await cross_rerank(question, ranked, top_k=8)
    except Exception:
        logger.exception("[Pipeline] Rerank 失败")
        reranked = ranked[:8]
    logger.info("[Pipeline] Step 6 完成: %d reranked", len(reranked))

    # ---- Step 7: Compress ----
    final_chunks = compress(reranked, max_tokens=max_tokens)
    logger.info("[Pipeline] Step 7 完成: %d final chunks", len(final_chunks))

    # ---- Step 8: Citation + Generate ----
    yield DeepSearchEvent(type="status", message="正在生成回答...")
    prompt, citations, source_dicts = build_citation_prompt(final_chunks, question)

    # 发送 sources
    yield DeepSearchEvent(type="sources", sources=source_dicts)

    # 发送 citation refs
    yield DeepSearchEvent(
        type="citation",
        citations=[{"source_id": c.source_id, "url": c.url, "title": c.title}
                    for c in citations],
    )

    # LLM 流式生成
    try:
        llm = create_llm_provider()
        full = ""
        async for chunk in llm.astream_generate(prompt):
            full += chunk
            yield DeepSearchEvent(type="content", content=chunk)
            await asyncio.sleep(0.01)  # 模拟流式延迟
    except Exception as e:
        logger.exception("[Pipeline] LLM 生成失败")
        yield DeepSearchEvent(type="error", message=f"生成回答失败: {e}")
        return

    elapsed = time.time() - t0
    logger.info("[Pipeline] 完成 in %.1fs (queries=%d sources=%d final_chunks=%d)",
                elapsed, len(queries), len(raw_results), len(final_chunks))
    yield DeepSearchEvent(type="done", execution_time=round(elapsed, 2))


def _raw_to_chunks(results: List[RawSearchResult]) -> List[ExtractedChunk]:
    chunks = []
    for i, r in enumerate(results):
        chunks.append(ExtractedChunk(
            chunk_id=f"raw_{i}", text=r.content,
            source_url=r.url, source_title=r.title, chunk_index=i,
        ))
    return chunks


def _fallback_rank(chunks: List[ExtractedChunk], top_k: int) -> List[RankedChunk]:
    ranked = []
    for i, c in enumerate(chunks[:top_k], 1):
        ranked.append(RankedChunk(
            chunk_id=c.chunk_id, text=c.text,
            source_url=c.source_url, source_title=c.source_title,
            chunk_index=c.chunk_index, relevance_score=0.5, rank=i,
        ))
    return ranked
