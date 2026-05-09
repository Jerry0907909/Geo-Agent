"""查询优化器

提供查询改写、扩展、多查询生成等功能，提高检索效果。
"""

from typing import List, Optional
import logging

from src.core.llm_provider import LLMProvider, create_llm_provider
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """查询优化器：改写、扩展、多角度查询
    
    通过LLM对用户查询进行优化，提高检索准确性。
    """
    
    def __init__(self, llm: Optional[LLMProvider] = None):
        """初始化查询优化器
        
        Args:
            llm: LLM提供者，为None则自动创建
        """
        self._llm = llm
    
    @property
    def llm(self) -> LLMProvider:
        """延迟加载LLM"""
        if self._llm is None:
            self._llm = create_llm_provider()
        return self._llm
    
    def rewrite_query(self, query: str) -> str:
        """查询改写：将用户查询改写为更专业的表达
        
        Args:
            query: 原始查询
            
        Returns:
            改写后的查询
        """
        prompt = f"""你是地质学专家，请将下面的查询改写为更专业、更精确的表达。

用户查询：{query}

改写要求：
1. 使用地质学专业术语
2. 保持查询意图不变
3. 只返回改写后的查询，不要其他内容

改写后的查询："""
        
        try:
            result = self.llm.generate(prompt, max_tokens=200).strip()
            logger.debug(f"查询改写: '{query}' -> '{result}'")
            return result
        except Exception as e:
            logger.warning(f"查询改写失败: {e}")
            return query
    
    def expand_query(self, query: str, num_variants: int = 3) -> List[str]:
        """查询扩展：生成相关的多个查询变体
        
        Args:
            query: 原始查询
            num_variants: 生成变体数量
            
        Returns:
            查询列表（包含原始查询）
        """
        prompt = f"""基于以下查询，生成{num_variants}个相关的查询变体，从不同角度探索同一主题。

原始查询：{query}

要求：
1. 每个变体应该从不同角度提问
2. 使用同义词、相关概念
3. 每行一个查询
4. 不要编号，不要其他解释

查询变体："""
        
        try:
            response = self.llm.generate(prompt, max_tokens=300)
            queries = [q.strip() for q in response.split('\n') if q.strip()]
            # 过滤掉太短的结果
            queries = [q for q in queries if len(q) > 5]
            result = [query] + queries[:num_variants]
            logger.debug(f"查询扩展: 生成 {len(result)} 个查询")
            return result
        except Exception as e:
            logger.warning(f"查询扩展失败: {e}")
            return [query]
    
    def generate_hypothetical_document(self, query: str) -> str:
        """HyDE: 生成假设性文档
        
        通过LLM生成一个假设性的答案文档，用于向量检索。
        
        Args:
            query: 用户查询
            
        Returns:
            假设性文档内容
        """
        prompt = f"""假设你是地质学专家，请根据以下问题，写一段假设性的答案（不必完全准确，但要专业）。

问题：{query}

假设性答案（200字以内）："""
        
        try:
            result = self.llm.generate(prompt, max_tokens=300).strip()
            logger.debug(f"生成假设性文档: {len(result)} 字符")
            return result
        except Exception as e:
            logger.warning(f"生成假设性文档失败: {e}")
            return query
    
    def extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词
        
        Args:
            query: 用户查询
            
        Returns:
            关键词列表
        """
        prompt = f"""从以下地质学相关查询中提取关键词和专业术语。

查询：{query}

要求：
1. 提取最重要的3-5个关键词
2. 优先提取地质学专业术语
3. 每行一个关键词
4. 不要编号

关键词："""
        
        try:
            response = self.llm.generate(prompt, max_tokens=100)
            keywords = [k.strip() for k in response.split('\n') if k.strip()]
            keywords = [k for k in keywords if len(k) > 1]
            logger.debug(f"提取关键词: {keywords}")
            return keywords[:5]
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return []
    
    def optimize(
        self,
        query: str,
        rewrite: bool = True,
        expand: bool = False,
        extract_keywords: bool = False
    ) -> dict:
        """综合查询优化
        
        Args:
            query: 原始查询
            rewrite: 是否改写查询
            expand: 是否扩展查询
            extract_keywords: 是否提取关键词
            
        Returns:
            优化结果字典
        """
        result = {
            "original": query,
            "rewritten": query,
            "expanded": [query],
            "keywords": []
        }
        
        if rewrite:
            result["rewritten"] = self.rewrite_query(query)
        
        if expand:
            result["expanded"] = self.expand_query(
                result["rewritten"] if rewrite else query
            )
        
        if extract_keywords:
            result["keywords"] = self.extract_keywords(query)
        
        return result


class MultiQueryRetriever:
    """多查询检索器：生成多个查询并融合结果"""
    
    def __init__(
        self,
        base_retriever,
        query_optimizer: Optional[QueryOptimizer] = None,
        num_queries: int = 3
    ):
        """初始化
        
        Args:
            base_retriever: 基础检索器
            query_optimizer: 查询优化器
            num_queries: 生成的查询数量
        """
        self.base_retriever = base_retriever
        self.query_optimizer = query_optimizer or QueryOptimizer()
        self.num_queries = num_queries
    
    def retrieve(self, query: str, top_k: int = 5) -> list:
        """多查询检索
        
        Args:
            query: 原始查询
            top_k: 返回文档数量
            
        Returns:
            检索结果文档列表
        """
        # 1. 生成多个查询
        queries = self.query_optimizer.expand_query(query, self.num_queries)
        
        # 2. 对每个查询检索
        doc_scores = {}
        
        for q in queries:
            try:
                docs = self.base_retriever.retrieve(q, top_k=top_k * 2)
                for doc in docs:
                    # 使用内容hash作为文档ID
                    doc_id = hash(doc.page_content[:200])
                    if doc_id not in doc_scores:
                        doc_scores[doc_id] = {'doc': doc, 'count': 0, 'queries': []}
                    doc_scores[doc_id]['count'] += 1
                    doc_scores[doc_id]['queries'].append(q)
            except Exception as e:
                logger.warning(f"检索查询 '{q}' 失败: {e}")
        
        # 3. 按出现次数排序（出现在多个查询结果中的文档更相关）
        ranked = sorted(
            doc_scores.values(),
            key=lambda x: x['count'],
            reverse=True
        )
        
        # 4. 添加元数据
        result_docs = []
        for item in ranked[:top_k]:
            doc = item['doc']
            doc.metadata['multi_query_count'] = item['count']
            doc.metadata['matched_queries'] = item['queries']
            result_docs.append(doc)
        
        logger.info(f"多查询检索完成: {len(queries)} 查询, {len(result_docs)} 结果")
        return result_docs


def create_query_optimizer(llm: Optional[LLMProvider] = None) -> QueryOptimizer:
    """创建查询优化器
    
    Args:
        llm: LLM提供者
        
    Returns:
        QueryOptimizer 实例
    """
    return QueryOptimizer(llm=llm)
