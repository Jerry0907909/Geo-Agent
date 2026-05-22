"""Tavily Search Engine — 异步原生 httpx 调用，不依赖 tavily-python SDK"""

import logging
import asyncio
import random
from typing import List, Optional

import httpx

from src.search.schemas import RawSearchResult
from src.utils.config import get_config

logger = logging.getLogger(__name__)

TAVILY_API = "https://api.tavily.com/search"
SOURCE_BOOST: dict[str, float] = {
    "academic": 0.12, "official": 0.08, "news": 0.05, "general": 0.0,
}

# 中文优先域名
ZH_PREFERRED_DOMAINS = [
    "xinhuanet.com", "people.com.cn", "chinanews.com",
    "thepaper.cn", "sina.com.cn", "sohu.com", "qq.com",
    "baidu.com", "zhihu.com", "wikipedia.org",
    "cnki.net", "wanfangdata.com.cn", "gov.cn", "edu.cn",
]


async def search(
    query: str,
    max_results: int = 5,
    *,
    time_range: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    depth: str = "advanced",
) -> List[RawSearchResult]:
    """执行单次 Tavily 搜索"""
    config = get_config()
    api_key = config.get("web_search.tavily_api_key") or _env("TAVILY_API_KEY", "")

    if not api_key:
        logger.warning("[Tavily] API key 未配置")
        return []

    body = {
        "api_key": api_key,
        "query": query,
        "search_depth": depth,
        "max_results": min(max_results, 20),
        "include_answer": True,
        "time_range": time_range or "year",
    }
    if include_domains:
        body["include_domains"] = include_domains[:30]

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        for attempt in range(3):
            try:
                resp = await client.post(TAVILY_API, json=body)
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    delay = 0.3 * (2 ** attempt) + random.uniform(0, 0.1)
                    logger.warning("[Tavily] 第 %d 次失败 (retry %.1fs): %s", attempt + 1, delay, e)
                    await asyncio.sleep(delay)
                else:
                    logger.warning("[Tavily] 3 次均失败: %s", e)
                    return []

    raw = data.get("results", []) if isinstance(data, dict) else []
    results = []
    for r in raw:
        results.append(RawSearchResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            content=r.get("content", "") or r.get("snippet", ""),
            score=float(r.get("score", 0.5)),
            published_date=r.get("published_date"),
        ))
    return results


async def search_multi(
    queries: List[str],
    max_results_per: int = 5,
    *,
    time_range: Optional[str] = None,
    depth: str = "advanced",
) -> List[RawSearchResult]:
    """并发搜索多个查询，按相关度去重合并"""
    if not queries:
        return []

    tasks = [
        search(q, max_results=max_results_per, time_range=time_range, depth=depth,
               include_domains=ZH_PREFERRED_DOMAINS if _is_chinese(q) else None)
        for q in queries
    ]
    all_batches = await asyncio.gather(*tasks, return_exceptions=True)

    seen = set()
    merged = []
    for batch in all_batches:
        if isinstance(batch, list):
            for r in batch:
                key = r.url
                if key not in seen:
                    seen.add(key)
                    merged.append(r)

    merged.sort(key=lambda r: r.score, reverse=True)
    logger.info("[Tavily] 并发搜索 %d queries → %d 条去重后结果", len(queries), len(merged))
    return merged


def _is_chinese(text: str) -> bool:
    import re
    return bool(re.search(r'[一-鿿]', text))


def _env(key: str, default: str) -> str:
    import os
    return os.getenv(key, default)
