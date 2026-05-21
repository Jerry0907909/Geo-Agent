"""WebSearch 工具 - 基于 Tavily Search API + DuckDuckGo 回退

优化策略（中文互联网优先）：
- 双轮搜索：先搜中文优先域名 → 质量不足则放开全互联网
- 中文内容过滤：仅保留标题或正文含中文字符的结果
- 智能时效性检测 + 近年加权 + 动态裁剪条数
"""

import logging
import time as time_module
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

from src.utils.config import get_config

logger = logging.getLogger(__name__)

SOURCE_BOOST: Dict[str, float] = {
    "academic": 0.12,
    "official": 0.08,
    "news": 0.05,
    "general": 0.0,
}

FETCH_MULTIPLIER = 3
MIN_RESULTS = 3
MAX_RESULTS = 10
QUALITY_THRESHOLD = 0.5

# 时效性关键词
FRESH_KEYWORDS = [
    "今天", "今日", "刚刚", "最新", "最近", "近期", "本周", "本月",
    "今年", "新闻", "快讯", "热点", "突发",
]
RECENT_KEYWORDS = [
    "进展", "趋势", "发展", "现状", "最新研究", "技术前沿",
]

# 中文优先域名（双轮策略第 1 轮）
ZH_PREFERRED_DOMAINS = [
    "xinhuanet.com", "people.com.cn", "chinanews.com", "chinadaily.com.cn",
    "thepaper.cn", "ifeng.com", "sina.com.cn", "sohu.com", "qq.com",
    "163.com", "toutiao.com", "guancha.cn", "cctv.com",
    "baidu.com", "zhihu.com", "wikipedia.org",
    "cnki.net", "wanfangdata.com.cn", "cqvip.com",
    "sciencedirect.com", "springer.com",
    "gov.cn", "edu.cn",
    "cgs.gov.cn", "geoscience.cn", "igg.cas.cn",
]


@dataclass
class SearchResult:
    title: str
    snippet: str
    url: str
    source_type: str
    relevance_score: float = 0.0
    publish_date: Optional[str] = None


class WebSearchTool:

    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        config = get_config()
        ws_cfg = config.config.get("web_search", {})
        self._tavily_api_key = ws_cfg.get("tavily_api_key") or ""
        self._search_depth = ws_cfg.get("search_depth", "advanced")
        self._language_preference = ws_cfg.get("language_preference", "zh")
        self._include_domains = ws_cfg.get("include_domains") or None
        self._exclude_domains = ws_cfg.get("exclude_domains") or None
        self._topic = ws_cfg.get("topic", "general")
        self._default_time_range = ws_cfg.get("default_time_range", "year")

    # ========== public ==========

    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        k = max_results if max_results is not None else self.max_results

        try:
            if self._tavily_api_key:
                results = self._dual_pass_search(query, k)
            else:
                results = self._search_duckduckgo(query, k * FETCH_MULTIPLIER)

            if not results:
                return []

            processed = self._process_results(results)
            unique = self._deduplicate(processed)
            sorted_results = sorted(unique, key=lambda x: x.relevance_score, reverse=True)
            return self._dynamic_slice(sorted_results, k)

        except Exception as e:
            logger.error("WebSearch 失败: %s", e)
            return []

    # ========== 双轮搜索（中文优先） ==========

    def _dual_pass_search(self, query: str, k: int) -> List[SearchResult]:
        optimized = self._optimize_query(query)

        # 第 1 轮：中文优先域名
        round1_domains = self._include_domains or ZH_PREFERRED_DOMAINS
        round1 = self._tavily_search(optimized, k * FETCH_MULTIPLIER, round1_domains)

        high_q = sum(1 for r in round1 if r.relevance_score >= QUALITY_THRESHOLD)
        if high_q >= 5:
            logger.info("[双轮] 中文优先足够 (high=%d/%d)", high_q, len(round1))
            return round1

        # 第 2 轮：全互联网
        logger.info("[双轮] 第1轮不足 (high=%d/%d) → 全互联网搜索", high_q, len(round1))
        round2 = self._tavily_search(optimized, k * FETCH_MULTIPLIER, None)

        seen = {self._domain_key(r.url) for r in round1}
        merged = list(round1)
        for r in round2:
            if self._domain_key(r.url) not in seen:
                merged.append(r)
                seen.add(self._domain_key(r.url))

        logger.info("[双轮] 合并: %d 条 (r1=%d r2=%d)", len(merged), len(round1), len(round2))
        return merged

    # ========== Tavily 单次搜索 ==========

    def _tavily_search(
        self, query: str, max_results: int, include_domains: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self._tavily_api_key)
            time_range, topic = self._detect_time_range(query)

            kwargs: Dict[str, Any] = {
                "query": query,
                "search_depth": self._search_depth,
                "max_results": min(max_results, 20),
                "include_answer": True,
                "time_range": time_range,
            }
            if topic and topic != "general":
                kwargs["topic"] = topic
            if include_domains:
                kwargs["include_domains"] = include_domains[:30]
            if self._exclude_domains:
                kwargs["exclude_domains"] = self._exclude_domains

            logger.info(
                "[Tavily] query='%s' max=%d time=%s domains=%d",
                query[:50], max_results, time_range,
                len(include_domains) if include_domains else 0,
            )
            result = client.search(**kwargs)
            raw = result.get("results", []) if isinstance(result, dict) else []
            now_year = time_module.localtime().tm_year

            results = []
            for r in raw:
                title = r.get("title", "")
                url = r.get("url", "")
                content = r.get("content", "") or r.get("snippet", "")
                if not title or not url:
                    continue
                # 中文过滤
                if self._language_preference == "zh" and not self._has_chinese(title + content[:120]):
                    continue
                raw_score = float(r.get("score", 0.5))
                raw_date = r.get("published_date", "")
                st = self._classify_source(url)
                boost = SOURCE_BOOST.get(st, 0.0)
                recency = self._recency_boost(raw_date, now_year)
                results.append(SearchResult(
                    title=title, snippet=content or title, url=url,
                    source_type=st,
                    relevance_score=min(raw_score + boost + recency, 1.0),
                    publish_date=raw_date or None,
                ))
            return results

        except ImportError:
            logger.warning("tavily-python 未安装 → DuckDuckGo")
            return self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.warning("Tavily 搜索失败: %s → DuckDuckGo", e)
            return self._search_duckduckgo(query, max_results)

    # ========== DuckDuckGo ==========

    def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            raw = ddgs.text(query, region="cn-zh", max_results=max_results * 2)
            results = []
            if raw:
                for r in raw:
                    if not r:
                        continue
                    t, b, h = r.get("title", ""), r.get("body", ""), r.get("href", "")
                    if not t or not h:
                        continue
                    st = self._classify_source(h)
                    results.append(SearchResult(
                        title=t, snippet=b or t, url=h, source_type=st,
                        relevance_score=0.5 + SOURCE_BOOST.get(st, 0.0),
                    ))
            logger.info("[DuckDuckGo] %d 条", len(results))
            return results
        except ImportError:
            logger.error("ddgs 未安装")
            return []
        except Exception as e:
            logger.error("DuckDuckGo 失败: %s", e)
            return []

    # ========== 查询优化 ==========

    def _optimize_query(self, query: str) -> str:
        """中文查询优化：保持原意，去除冗余"""
        q = query.strip()
        # 去常见冗余前缀
        for prefix in ["请帮我", "帮我", "请问", "我想知道", "我想了解"]:
            if q.startswith(prefix) and len(q) > len(prefix) + 3:
                q = q[len(prefix):]
        # 限制长度
        if len(q) > 200:
            q = q[:200]
        return q

    # ========== 中文检测 ==========

    @staticmethod
    def _has_chinese(text: str) -> bool:
        return bool(re.search(r'[一-鿿]', text))

    # ========== 时效性 ==========

    def _detect_time_range(self, query: str) -> Tuple[str, Optional[str]]:
        q = query.lower()
        fresh = sum(1 for kw in FRESH_KEYWORDS if kw in q)
        recent = sum(1 for kw in RECENT_KEYWORDS if kw in q)

        if fresh >= 2:
            return ("week", "news")
        if fresh >= 1:
            return ("month", "news")
        if recent >= 2:
            return ("month", None)
        if recent >= 1 or self._looks_like_current_events(q):
            return ("year", None)
        return (self._default_time_range, None)

    def _looks_like_current_events(self, q: str) -> bool:
        cy = str(time_module.localtime().tm_year)
        return cy in q or any(w in q for w in ["现在", "当前", "目前", "最近"])

    def _recency_boost(self, date_str: str, now_year: int) -> float:
        if not date_str:
            return 0.0
        try:
            for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
                try:
                    year = time_module.strptime(date_str[:10], fmt).tm_year
                    break
                except ValueError:
                    continue
            else:
                m = re.search(r"(\d{4})", date_str)
                year = int(m.group(1)) if m else now_year - 5
        except Exception:
            return 0.0

        delta = now_year - year
        if delta <= 0:
            return 0.12
        if delta == 1:
            return 0.08
        if delta == 2:
            return 0.03
        if delta <= 5:
            return 0.0
        return -0.15

    # ========== 动态裁剪 ==========

    def _dynamic_slice(self, sorted_results: List[SearchResult], max_k: int) -> List[SearchResult]:
        if not sorted_results:
            return []
        high = [r for r in sorted_results if r.relevance_score >= QUALITY_THRESHOLD]
        low = [r for r in sorted_results if r.relevance_score < QUALITY_THRESHOLD]

        if len(high) >= 8:
            return high[:min(max_k, len(high))]
        if len(high) >= 5:
            return high + low[:max(0, min(3, max_k - len(high)))]
        if len(high) >= 2:
            return high + low[:max(1, min(MIN_RESULTS - len(high), len(low)))]
        return sorted_results[:max(MIN_RESULTS, min(3, len(sorted_results)))]

    # ========== 文本处理 ==========

    def _classify_source(self, url: str) -> str:
        u = url.lower()
        if any(d in u for d in ['cnki.net', 'wanfangdata', 'cqvip', 'sciencedirect',
                                 'springer', 'arxiv.org', 'nature.com']):
            return 'academic'
        if any(d in u for d in ['xinhuanet', 'people.com', 'chinanews', 'sina.com',
                                 'sohu.com', 'thepaper.cn', 'ifeng.com']):
            return 'news'
        if '.gov.cn' in u or '.edu.cn' in u:
            return 'official'
        return 'general'

    def _process_results(self, results: List[SearchResult]) -> List[SearchResult]:
        for r in results:
            r.title = self._clean_text(r.title)
            r.snippet = self._clean_text(r.snippet)
        return results

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            dk = self._domain_key(r.url)
            # 额外检测：标题高度相似也视为重复
            title_key = r.title[:30]
            if dk not in seen and title_key not in seen:
                seen.add(dk)
                seen.add(title_key)
                unique.append(r)
        return unique

    @staticmethod
    def _domain_key(url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return url

    # ========== 格式化 ==========

    def format_for_llm(self, results: List[SearchResult], max_snippet_chars: int = 300) -> str:
        if not results:
            return "(未检索到相关网络信息)"
        parts = []
        for i, r in enumerate(results, 1):
            label = {'academic': '学术', 'news': '新闻', 'official': '官方', 'general': '网络'}.get(r.source_type, '网络')
            snippet = r.snippet
            if len(snippet) > max_snippet_chars:
                snippet = snippet[:max_snippet_chars].rstrip() + "..."
            date_hint = f"({r.publish_date}) " if r.publish_date else ""
            parts.append(
                f"【来源{i} - {label}】{date_hint}\n"
                f"标题：{r.title}\n"
                f"内容：{snippet}\n"
                f"链接：{r.url}\n"
            )
        return "\n".join(parts)

    def get_source_links(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        return [{
            'id': i, 'title': r.title, 'url': r.url,
            'source_type': r.source_type, 'publish_date': r.publish_date,
            'snippet': r.snippet[:100] + '...' if len(r.snippet) > 100 else r.snippet,
        } for i, r in enumerate(results, 1)]


def create_web_search_tool() -> WebSearchTool:
    config = get_config()
    ws_cfg = config.config.get("web_search", {})
    max_results = ws_cfg.get("max_results", 10)
    return WebSearchTool(max_results=max_results)
