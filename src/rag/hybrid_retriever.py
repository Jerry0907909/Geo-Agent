"""混合检索器

实现向量检索 + BM25关键词检索的混合检索策略，提高检索精度。
"""

from typing import List, Optional, Dict, Any, Tuple
import logging

import jieba
from rank_bm25 import BM25Okapi

from langchain_core.documents import Document
from src.database.chroma_manager import ChromaManager, create_chroma_manager
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器：向量检索 + BM25关键词检索
    
    使用Reciprocal Rank Fusion (RRF)算法融合两种检索结果。
    """
    
    def __init__(
        self,
        vector_store: Optional[ChromaManager] = None,
        alpha: float = 0.5,
        use_jieba: bool = True
    ):
        """初始化混合检索器
        
        Args:
            vector_store: 向量存储管理器
            alpha: 向量检索权重 (0-1)，BM25权重为 1-alpha
            use_jieba: 是否使用结巴分词（中文）
        """
        self.vector_store = vector_store or create_chroma_manager()
        self.alpha = alpha
        self.beta = 1 - alpha
        self.use_jieba = use_jieba
        
        # BM25索引
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_docs: List[Document] = []
        self.tokenized_corpus: List[List[str]] = []
        
        # 加载配置
        config = get_config()
        rag_cfg = config.get_rag_config()
        self.default_top_k = rag_cfg.get("top_k", 5)
        
        logger.info(f"混合检索器初始化: alpha={alpha}, use_jieba={use_jieba}")
    
    def _tokenize(self, text: str) -> List[str]:
        """对文本进行分词
        
        Args:
            text: 输入文本
            
        Returns:
            分词结果列表
        """
        if self.use_jieba:
            # 使用结巴分词（中文优化）
            return list(jieba.cut(text))
        else:
            # 简单空格分词（英文）
            return text.lower().split()
    
    def build_bm25_index(self, documents: Optional[List[Document]] = None) -> None:
        """构建BM25索引
        
        Args:
            documents: 文档列表，如果为None则从向量库加载
        """
        if documents is None:
            # 从向量库加载所有文档
            try:
                collection = self.vector_store.collection
                result = collection.get()
                
                documents = []
                for i, doc_content in enumerate(result.get("documents", [])):
                    metadata = result.get("metadatas", [{}])[i] if result.get("metadatas") else {}
                    documents.append(Document(page_content=doc_content, metadata=metadata))
                
                logger.info(f"从向量库加载 {len(documents)} 个文档")
            except Exception as e:
                logger.error(f"从向量库加载文档失败: {e}")
                return
        
        if not documents:
            logger.warning("没有文档可用于构建BM25索引")
            return
        
        self.corpus_docs = documents
        
        # 分词
        self.tokenized_corpus = [
            self._tokenize(doc.page_content)
            for doc in documents
        ]
        
        # 构建BM25索引
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25索引构建完成，共 {len(documents)} 个文档")
    
    def _vector_search(self, query: str, top_k: int) -> List[Tuple[Document, float]]:
        """向量检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            (文档, 分数) 列表
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                top_k=top_k
            )
            return results
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    def _bm25_search(self, query: str, top_k: int) -> List[Tuple[Document, float]]:
        """BM25关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            (文档, 分数) 列表
        """
        if self.bm25 is None or not self.corpus_docs:
            logger.warning("BM25索引未构建")
            return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # 获取top_k结果
        doc_scores = list(zip(self.corpus_docs, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        return doc_scores[:top_k]
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_rrf: bool = True
    ) -> List[Document]:
        """混合检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            use_rrf: 是否使用RRF融合，否则使用加权求和
            
        Returns:
            检索到的文档列表
        """
        if top_k is None:
            top_k = self.default_top_k
        
        # 获取更多候选以便融合
        candidate_k = top_k * 3
        
        # 1. 向量检索
        vector_results = self._vector_search(query, candidate_k)
        
        # 2. BM25检索
        bm25_results = self._bm25_search(query, candidate_k)
        
        # 3. 融合结果
        if use_rrf:
            merged_docs = self._rrf_fusion(vector_results, bm25_results, top_k)
        else:
            merged_docs = self._weighted_fusion(vector_results, bm25_results, top_k)
        
        logger.info(f"混合检索完成，返回 {len(merged_docs)} 个文档")
        return merged_docs
    
    def _rrf_fusion(
        self,
        vector_results: List[Tuple[Document, float]],
        bm25_results: List[Tuple[Document, float]],
        top_k: int,
        k: int = 60
    ) -> List[Document]:
        """Reciprocal Rank Fusion融合
        
        RRF公式: score = sum(1 / (k + rank))
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            top_k: 返回数量
            k: RRF参数
            
        Returns:
            融合后的文档列表
        """
        doc_scores: Dict[str, Dict[str, Any]] = {}
        
        # 向量检索结果评分
        for rank, (doc, score) in enumerate(vector_results):
            doc_id = doc.page_content[:100]  # 使用内容前100字符作为ID
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "rrf_score": 0,
                    "vector_rank": None,
                    "bm25_rank": None
                }
            doc_scores[doc_id]["rrf_score"] += self.alpha / (k + rank + 1)
            doc_scores[doc_id]["vector_rank"] = rank + 1
        
        # BM25检索结果评分
        for rank, (doc, score) in enumerate(bm25_results):
            doc_id = doc.page_content[:100]
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "rrf_score": 0,
                    "vector_rank": None,
                    "bm25_rank": None
                }
            doc_scores[doc_id]["rrf_score"] += self.beta / (k + rank + 1)
            doc_scores[doc_id]["bm25_rank"] = rank + 1
        
        # 按RRF分数排序
        ranked_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        # 添加融合信息到metadata
        result_docs = []
        for item in ranked_docs[:top_k]:
            doc = item["doc"]
            doc.metadata["rrf_score"] = item["rrf_score"]
            doc.metadata["vector_rank"] = item["vector_rank"]
            doc.metadata["bm25_rank"] = item["bm25_rank"]
            result_docs.append(doc)
        
        return result_docs
    
    def _weighted_fusion(
        self,
        vector_results: List[Tuple[Document, float]],
        bm25_results: List[Tuple[Document, float]],
        top_k: int
    ) -> List[Document]:
        """加权分数融合
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            top_k: 返回数量
            
        Returns:
            融合后的文档列表
        """
        doc_scores: Dict[str, Dict[str, Any]] = {}
        
        # 归一化向量检索分数
        if vector_results:
            max_vector_score = max(score for _, score in vector_results) or 1
            for doc, score in vector_results:
                doc_id = doc.page_content[:100]
                normalized_score = score / max_vector_score
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {"doc": doc, "score": 0}
                doc_scores[doc_id]["score"] += self.alpha * normalized_score
        
        # 归一化BM25分数
        if bm25_results:
            max_bm25_score = max(score for _, score in bm25_results) or 1
            for doc, score in bm25_results:
                doc_id = doc.page_content[:100]
                normalized_score = score / max_bm25_score
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {"doc": doc, "score": 0}
                doc_scores[doc_id]["score"] += self.beta * normalized_score
        
        # 排序
        ranked = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [item["doc"] for item in ranked[:top_k]]


def create_hybrid_retriever(
    vector_store: Optional[ChromaManager] = None,
    alpha: float = 0.5,
    build_index: bool = True
) -> HybridRetriever:
    """创建混合检索器
    
    Args:
        vector_store: 向量存储管理器
        alpha: 向量检索权重
        build_index: 是否立即构建BM25索引
        
    Returns:
        HybridRetriever 实例
    """
    retriever = HybridRetriever(
        vector_store=vector_store,
        alpha=alpha
    )
    
    if build_index:
        retriever.build_bm25_index()
    
    return retriever
