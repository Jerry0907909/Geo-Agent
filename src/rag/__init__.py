"""RAG模块

提供检索增强生成(RAG)相关功能，包括：
- 文档检索
- 混合检索（向量+BM25）
- 重排序
- 查询优化
"""

from src.rag.retriever import RAGRetriever, create_rag_retriever
from src.rag.chain import RAGChain, create_rag_chain
from src.rag.hybrid_retriever import HybridRetriever, create_hybrid_retriever
from src.rag.reranker import Reranker, RerankerRetriever, create_reranker
from src.rag.query_optimizer import (
    QueryOptimizer,
    MultiQueryRetriever,
    create_query_optimizer,
)

__all__ = [
    # 基础检索
    "RAGRetriever",
    "create_rag_retriever",
    # RAG Chain
    "RAGChain",
    "create_rag_chain",
    # 混合检索
    "HybridRetriever",
    "create_hybrid_retriever",
    # 重排序
    "Reranker",
    "RerankerRetriever",
    "create_reranker",
    # 查询优化
    "QueryOptimizer",
    "MultiQueryRetriever",
    "create_query_optimizer",
]