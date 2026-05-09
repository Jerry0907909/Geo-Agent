"""WebSearch 工具 - 中文互联网实时信息检索

功能：
1. 搜索中文互联网获取实时信息
2. 内容去重、摘要提取、结构化处理
3. 返回带来源链接的标准化数据
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    title: str
    snippet: str
    url: str
    source_type: str  # news, academic, official, general
    relevance_score: float = 0.0
    publish_date: Optional[str] = None


class WebSearchTool:
    """WebSearch 工具类
    
    使用搜索 API 获取中文互联网信息，并进行结构化处理
    """
    
    def __init__(self, max_results: int = 5):
        """初始化 WebSearch 工具
        
        Args:
            max_results: 最大返回结果数
        """
        self.max_results = max_results
        
    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        k = max_results if max_results is not None else self.max_results
        
        try:
            # TODO: 集成实际的搜索 API
            # 可选方案：
            # 1. DuckDuckGo API (免费，无需 API key)
            # 2. Bing Search API
            # 3. Google Custom Search API
            # 4. SerpAPI (付费但功能强大)
            
            # 临时实现：使用 DuckDuckGo
            results = self._search_duckduckgo(query, k)
            
            # 内容处理
            processed_results = self._process_results(results)
            
            # 去重
            unique_results = self._deduplicate(processed_results)
            
            # 按相关度排序
            sorted_results = sorted(
                unique_results, 
                key=lambda x: x.relevance_score, 
                reverse=True
            )
            
            return sorted_results[:k]
            
        except Exception as e:
            logger.error(f"WebSearch 失败: {e}")
            return []
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """使用 DuckDuckGo 搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        try:
            from ddgs import DDGS
            
            logger.info(f"[WebSearch] 开始搜索: query='{query}', max_results={max_results}")
            
            results = []
            # 使用新的 API
            ddgs = DDGS()
            
            # 使用中文搜索
            search_results = ddgs.text(
                query, 
                region='cn-zh',  # 中文区域
                max_results=max_results * 2  # 获取更多结果用于筛选
            )
            
            # 处理结果
            if search_results:
                for r in search_results:
                    if not r:  # 跳过空结果
                        continue
                    
                    title = r.get('title', '')
                    body = r.get('body', '')
                    href = r.get('href', '')
                    
                    # 跳过无效结果
                    if not title or not href:
                        continue
                    
                    result = SearchResult(
                        title=title,
                        snippet=body or title,  # 如果没有 body，使用 title
                        url=href,
                        source_type=self._classify_source(href),
                        relevance_score=0.8
                    )
                    results.append(result)
                    
                    logger.info(f"  [WebSearch] 结果: {title[:50]}... | {href}")
            
            logger.info(f"[WebSearch] 搜索完成: 获取到 {len(results)} 条有效结果")
            return results
            
        except ImportError as e:
            logger.error(f"ddgs 未安装: {e}")
            logger.error("请运行: pip install ddgs")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _classify_source(self, url: str) -> str:
        """分类信息来源类型
        
        Args:
            url: 来源 URL
            
        Returns:
            来源类型
        """
        url_lower = url.lower()
        
        # 学术来源
        if any(domain in url_lower for domain in ['cnki.net', 'wanfangdata', 'cqvip', 'sciencedirect', 'springer']):
            return 'academic'
        
        # 新闻来源
        if any(domain in url_lower for domain in ['xinhuanet', 'people.com', 'chinanews', 'sina.com', 'sohu.com']):
            return 'news'
        
        # 官方来源
        if '.gov.cn' in url_lower or '.edu.cn' in url_lower:
            return 'official'
        
        return 'general'
    
    def _process_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """处理搜索结果
        
        Args:
            results: 原始搜索结果
            
        Returns:
            处理后的结果
        """
        processed = []
        
        for result in results:
            # 清理标题和摘要
            result.title = self._clean_text(result.title)
            result.snippet = self._clean_text(result.snippet)
            
            # 计算相关度（简单实现，可以改进）
            if result.source_type in ['academic', 'official']:
                result.relevance_score = 0.9
            elif result.source_type == 'news':
                result.relevance_score = 0.7
            else:
                result.relevance_score = 0.6
            
            processed.append(result)
        
        return processed
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 去除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：""''（）、]', '', text)
        
        return text
    
    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重搜索结果
        
        Args:
            results: 搜索结果列表
            
        Returns:
            去重后的结果
        """
        seen_hashes = set()
        unique_results = []
        
        for result in results:
            # 基于标题和摘要生成哈希
            content = f"{result.title}{result.snippet}"
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def format_for_llm(self, results: List[SearchResult]) -> str:
        """格式化搜索结果供 LLM 使用
        
        Args:
            results: 搜索结果列表
            
        Returns:
            格式化的文本
        """
        if not results:
            return "(未检索到相关网络信息)"
        
        formatted_parts = []
        for i, result in enumerate(results, 1):
            source_label = {
                'academic': '学术',
                'news': '新闻',
                'official': '官方',
                'general': '网络'
            }.get(result.source_type, '网络')
            
            part = f"""【来源{i} - {source_label}】
标题：{result.title}
内容：{result.snippet}
链接：{result.url}
"""
            formatted_parts.append(part)
        
        return "\n".join(formatted_parts)
    
    def get_source_links(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """获取来源链接数据（供前端显示）
        
        Args:
            results: 搜索结果列表
            
        Returns:
            链接数据列表
        """
        links = []
        for i, result in enumerate(results, 1):
            links.append({
                'id': i,
                'title': result.title,
                'url': result.url,
                'source_type': result.source_type,
                'snippet': result.snippet[:100] + '...' if len(result.snippet) > 100 else result.snippet
            })
        return links


def create_web_search_tool() -> WebSearchTool:
    """创建 WebSearch 工具实例"""
    return WebSearchTool(max_results=5)
