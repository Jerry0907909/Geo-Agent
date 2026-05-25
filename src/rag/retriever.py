"""RAG Retriever - 基于 LangChain v1 的检索增强生成

使用 LangChain v1 的检索策略：
- MultiQueryRetriever: 生成多个查询变体提高召回率
- 结果去重和多样性排序
- 语义相似度 + 关键词匹配混合检索
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Iterator, Any, Dict, Set

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document

from src.core.llm_provider import LLMProvider, create_llm_provider
from src.core.prompts import get_rag_system_prompt, get_rag_user_prompt
from src.database.chroma_manager import ChromaManager, create_chroma_manager, search_all_collections
from src.rag.prompt_templates import build_context_from_documents
from src.utils.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """RAG 检索与生成的结果"""

    question: str
    answer: str
    context_documents: List[Document] = field(default_factory=list)


# RAG 提示词（从 prompts 模块获取，这里保留默认值作为备用）
RAG_SYSTEM_PROMPT = get_rag_system_prompt()
RAG_USER_PROMPT = get_rag_user_prompt()


class RAGRetriever:
    """RAG 检索器 - 基于 LangChain LCEL
    
    使用 LangChain Expression Language 构建 RAG 链。
    """

    def __init__(
        self,
        vector_store: ChromaManager,
        llm_provider: LLMProvider,
        default_top_k: Optional[int] = None,
    ) -> None:
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.llm = llm_provider.get_langchain_llm()

        config = get_config()
        rag_cfg = config.get_rag_config()
        self.default_top_k = int(
            default_top_k if default_top_k is not None else rag_cfg.get("top_k", 5)
        )
        
        # 构建 RAG 提示词模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT),
            ("human", RAG_USER_PROMPT),
        ])
        
        # 输出解析器
        self.output_parser = StrOutputParser()

    def _generate_query_variations(self, query: str, num_variations: int = 3) -> List[str]:
        """使用 LLM 生成查询变体（MultiQuery 策略）
        
        Args:
            query: 原始查询
            num_variations: 生成变体数量
            
        Returns:
            包含原始查询和变体的列表
        """
        queries = [query]  # 始终包含原始查询
        
        try:
            # 使用 LLM 生成查询变体
            variation_prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个查询改写专家。给定一个用户问题，生成{num}个不同角度的相关查询变体。
这些变体应该：
1. 保持原始问题的核心意图
2. 使用不同的措辞和关键词
3. 从不同角度描述同一个信息需求

只输出查询变体，每行一个，不要编号或其他说明。"""),
                ("human", "原始问题：{query}\n\n请生成{num}个查询变体：")
            ])
            
            chain = variation_prompt | self.llm | StrOutputParser()
            # 设置较短的超时，避免 MultiQuery 拖慢整体响应
            result = chain.invoke(
                {"query": query, "num": num_variations},
                config={"timeout": 15}
            )
            
            # 解析生成的变体
            for line in result.strip().split("\n"):
                line = line.strip()
                # 去除可能的编号
                line = re.sub(r'^[\d]+[.、)\]\s]+', '', line).strip()
                if line and line != query and len(line) > 5:
                    queries.append(line)
            
            logger.info(f"[MultiQuery] 原始查询: {query}")
            logger.info(f"[MultiQuery] 生成 {len(queries)-1} 个变体: {queries[1:]}")
            
        except Exception as e:
            logger.warning(f"[MultiQuery] 生成查询变体失败: {e}，使用原始查询")
        
        return queries[:num_variations + 1]  # 限制总数
    
    def _deduplicate_documents(self, documents: List[Document], max_per_source: int = 2) -> List[Document]:
        """文档去重和多样性排序
        
        Args:
            documents: 原始文档列表
            max_per_source: 每个来源最多保留的文档数
            
        Returns:
            去重后的文档列表
        """
        seen_hashes: Set[int] = set()
        source_counts: Dict[str, int] = {}
        unique_docs: List[Document] = []
        
        for doc in documents:
            # 内容哈希去重
            content_hash = hash(doc.page_content[:300])
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            
            # 来源多样性控制
            source = doc.metadata.get("source", "unknown")
            if source_counts.get(source, 0) >= max_per_source:
                continue
            source_counts[source] = source_counts.get(source, 0) + 1
            
            unique_docs.append(doc)
        
        logger.info(f"[Dedup] 去重前: {len(documents)}, 去重后: {len(unique_docs)}, 来源分布: {source_counts}")
        return unique_docs

    def retrieve(self, query: str, top_k: Optional[int] = None, min_relevance_score: float = 0.0, use_multi_query: bool = False, search_all: bool = True, user_id: Optional[str] = None) -> List[Document]:
        """执行增强检索（LangChain v1 风格）

        默认不启用 MultiQuery（避免额外的 LLM 调用增加延迟）

        Args:
            query: 查询文本
            top_k: 返回文档数量
            min_relevance_score: 最小相关度阈值 (0.0-1.0)
            use_multi_query: 是否使用多查询策略（会增加一次 LLM 调用，仅大型知识库推荐启用）
            search_all: 是否搜索所有知识库
            user_id: 可选，限定搜索该用户的知识库文档
        """
        k = int(top_k if top_k is not None else self.default_top_k)

        # 构建用户过滤条件
        chroma_filter = None
        allowed_collections = None
        if user_id:
            chroma_filter = {"user_id": user_id}
            from src.database.chroma_manager import list_all_collections
            all_colls = list_all_collections()
            allowed_collections = [c for c in all_colls if c.startswith(f"user_{user_id}_")]

        # 生成查询变体（默认关闭以降低延迟）
        if use_multi_query:
            queries = self._generate_query_variations(query, num_variations=1)
        else:
            queries = [query]

        # 对每个查询执行检索
        all_docs: List[Document] = []
        doc_scores: Dict[int, float] = {}  # content_hash -> best_score

        for q in queries:
            # 检索更多文档用于后续筛选
            if search_all:
                docs = search_all_collections(query=q, top_k=k * 2, filter=chroma_filter, allowed_collections=allowed_collections)
            else:
                docs = self.vector_store.similarity_search(query=q, top_k=k * 2, filter=chroma_filter)
            
            for doc in docs:
                content_hash = hash(doc.page_content[:300])
                score = doc.metadata.get("relevance_score", 0)
                
                # 保留最高分数
                if content_hash not in doc_scores or score > doc_scores[content_hash]:
                    doc_scores[content_hash] = score
                    # 更新或添加文档
                    all_docs = [d for d in all_docs if hash(d.page_content[:300]) != content_hash]
                    all_docs.append(doc)
        
        # 按分数排序
        sorted_docs = sorted(all_docs, key=lambda d: d.metadata.get("relevance_score", 0), reverse=True)
        
        # 应用相关度阈值过滤
        if min_relevance_score > 0.0:
            filtered_docs = [
                doc for doc in sorted_docs 
                if doc.metadata.get("relevance_score", 0) >= min_relevance_score
            ]
            logger.info(f"[阈值过滤] 过滤前: {len(sorted_docs)}, 过滤后: {len(filtered_docs)}, 阈值: {min_relevance_score}")
            sorted_docs = filtered_docs
        
        # 去重和多样性筛选
        result_docs = self._deduplicate_documents(sorted_docs, max_per_source=2)
        
        return result_docs[:k]

    def _format_docs(self, docs: List[Document]) -> str:
        """将文档列表格式化为上下文字符串"""
        return build_context_from_documents(docs)

    def run(self, question: str, top_k: Optional[int] = None, min_relevance_score: float = 0.0, user_id: Optional[str] = None) -> RAGResult:
        """完整 RAG 流程：检索 + 生成"""
        # 1. 检索文档（用户级隔离）
        docs = self.retrieve(question, top_k=top_k, min_relevance_score=min_relevance_score, user_id=user_id)
        
        # 2. 格式化上下文
        context = self._format_docs(docs) if docs else "(未检索到相关文献片段)"
        
        # 3. 使用 LCEL 链生成答案
        chain = self.prompt | self.llm | self.output_parser
        answer = chain.invoke({
            "context": context,
            "question": question,
        })
        
        return RAGResult(
            question=question, 
            answer=answer, 
            context_documents=docs
        )
    
    def stream(self, question: str, top_k: Optional[int] = None, min_relevance_score: float = 0.0, user_id: Optional[str] = None) -> tuple[List[Document], Iterator[str]]:
        """流式 RAG：先返回检索文档，再流式生成答案

        Returns:
            (文档列表, 答案流式迭代器)
        """
        # 1. 检索文档
        docs = self.retrieve(question, top_k=top_k, min_relevance_score=min_relevance_score, user_id=user_id)
        
        # 2. 格式化上下文
        context = self._format_docs(docs) if docs else "(未检索到相关文献片段)"
        
        # 3. 创建流式生成器
        def answer_generator() -> Iterator[str]:
            chain = self.prompt | self.llm | self.output_parser
            for chunk in chain.stream({
                "context": context,
                "question": question,
            }):
                yield chunk
        
        return docs, answer_generator()

    async def astream(self, question: str, top_k: Optional[int] = None, min_relevance_score: float = 0.0, user_id: Optional[str] = None) -> tuple[List[Document], Any]:
        """异步流式 RAG：先返回检索文档，再流式生成答案

        Returns:
            (文档列表, 答案异步流式迭代器)
        """
        # 1. 检索文档 (目前 retrieve 仍为同步，若 Chroma 支持异步可优化)
        docs = self.retrieve(question, top_k=top_k, min_relevance_score=min_relevance_score, user_id=user_id)
        
        # 2. 格式化上下文
        context = self._format_docs(docs) if docs else "(未检索到相关文献片段)"
        
        # 3. 创建异步流式生成器
        async def answer_generator():
            chain = self.prompt | self.llm | self.output_parser
            async for chunk in chain.astream({
                "context": context,
                "question": question,
            }):
                yield chunk
        
        return docs, answer_generator()
    
    # 兼容旧接口
    def generate_answer(self, question: str, documents: Sequence[Document]) -> str:
        """基于检索到的文档和问题生成答案（兼容旧接口）"""
        context = self._format_docs(list(documents)) if documents else "(未检索到相关文献片段)"
        chain = self.prompt | self.llm | self.output_parser
        return chain.invoke({
            "context": context,
            "question": question,
        })


def create_rag_retriever() -> RAGRetriever:
    """根据全局配置创建默认 RAGRetriever 实例"""
    vector_store = create_chroma_manager()
    llm_provider = create_llm_provider()
    return RAGRetriever(vector_store=vector_store, llm_provider=llm_provider)
