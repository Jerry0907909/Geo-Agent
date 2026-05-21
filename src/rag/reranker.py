"""重排序器

使用交叉编码器对检索结果进行重新排序，提高检索精度。
"""

from typing import List, Optional, Tuple
import logging

from langchain_core.documents import Document
from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 全局模型缓存
_reranker_model = None


class Reranker:
    """重排序器：使用交叉编码器对检索结果重新排序
    
    交叉编码器直接计算查询和文档的相关性分数，
    比双塔模型（如向量检索）更准确，但计算成本更高。
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
        use_fp16: bool = True
    ):
        """初始化重排序器
        
        Args:
            model_name: 模型名称或路径
            device: 运行设备 ('cpu', 'cuda', 'mps')
            use_fp16: 是否使用FP16精度
        """
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None
        
        logger.info(f"重排序器配置: model={model_name}, device={device}")
    
    @property
    def model(self):
        """延迟加载模型"""
        global _reranker_model
        
        if self._model is not None:
            return self._model
        
        if _reranker_model is not None:
            self._model = _reranker_model
            return self._model
        
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"加载重排序模型: {self.model_name}")
            
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=512
            )
            
            # 缓存全局模型
            _reranker_model = self._model
            
            logger.info("重排序模型加载完成")
            return self._model
        
        except ImportError:
            logger.error("sentence-transformers未安装，请运行: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"加载重排序模型失败: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """对文档重新排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回的文档数量，默认返回全部
            
        Returns:
            重新排序后的文档列表
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = len(documents)
        
        try:
            # 构建查询-文档对
            pairs = [(query, doc.page_content) for doc in documents]
            
            # 计算相关性分数
            scores = self.model.predict(pairs, show_progress_bar=False)
            
            # 配对并排序
            doc_score_pairs = list(zip(documents, scores))
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 添加分数到metadata并返回
            result_docs = []
            for doc, score in doc_score_pairs[:top_k]:
                doc.metadata["rerank_score"] = float(score)
                result_docs.append(doc)
            
            logger.debug(f"重排序完成，返回 {len(result_docs)} 个文档")
            return result_docs
        
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 失败时返回原始顺序
            return documents[:top_k]
    
    def score(self, query: str, document: str) -> float:
        """计算单个查询-文档对的相关性分数
        
        Args:
            query: 查询文本
            document: 文档内容
            
        Returns:
            相关性分数
        """
        try:
            score = self.model.predict([(query, document)])[0]
            return float(score)
        except Exception as e:
            logger.error(f"计算分数失败: {e}")
            return 0.0


class RerankerRetriever:
    """集成Reranker的检索器
    
    先使用基础检索器获取候选文档，再使用Reranker重新排序。
    """
    
    def __init__(
        self,
        base_retriever,
        reranker: Optional[Reranker] = None,
        initial_k: int = 20,
        final_k: int = 5
    ):
        """初始化
        
        Args:
            base_retriever: 基础检索器（需要有retrieve方法）
            reranker: 重排序器
            initial_k: 初次检索数量
            final_k: 重排后保留数量
        """
        self.base_retriever = base_retriever
        self.reranker = reranker or Reranker()
        self.initial_k = initial_k
        self.final_k = final_k
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        """检索并重排序
        
        Args:
            query: 查询文本
            top_k: 最终返回数量，默认使用final_k
            
        Returns:
            检索并重排序后的文档列表
        """
        if top_k is None:
            top_k = self.final_k
        
        # 1. 初次检索获取更多候选
        candidates = self.base_retriever.retrieve(
            query=query,
            top_k=self.initial_k
        )
        
        if not candidates:
            return []
        
        # 2. Rerank重排序
        reranked_docs = self.reranker.rerank(
            query=query,
            documents=candidates,
            top_k=top_k
        )
        
        return reranked_docs


class LightweightReranker:
    """轻量级重排序器
    
    使用LLM进行重排序，不需要额外的模型。
    适用于无法加载交叉编码器模型的场景。
    """
    
    def __init__(self, llm=None):
        """初始化
        
        Args:
            llm: LLM提供者
        """
        self.llm = llm
    
    def _get_llm(self):
        """延迟获取LLM"""
        if self.llm is None:
            from src.core.llm_provider import create_llm_provider
            self.llm = create_llm_provider()
        return self.llm
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """使用LLM对文档进行相关性评分和排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回的文档数量
            
        Returns:
            重新排序后的文档列表
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = len(documents)
        
        try:
            llm = self._get_llm()
            
            # 为每个文档评分
            scored_docs = []
            for doc in documents:
                score = self._score_document(llm, query, doc.page_content)
                scored_docs.append((doc, score))
            
            # 排序
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # 添加分数到metadata
            result_docs = []
            for doc, score in scored_docs[:top_k]:
                doc.metadata["llm_rerank_score"] = score
                result_docs.append(doc)
            
            return result_docs
        
        except Exception as e:
            logger.error(f"LLM重排序失败: {e}")
            return documents[:top_k]
    
    def _score_document(self, llm, query: str, content: str) -> float:
        """使用LLM为单个文档评分
        
        Args:
            llm: LLM提供者
            query: 查询文本
            content: 文档内容
            
        Returns:
            相关性分数 (0-10)
        """
        prompt = f"""请评估以下文档与查询的相关性，返回1-10的分数（10表示高度相关）。

查询：{query}

文档内容：{content[:500]}

只返回一个数字分数，不要其他内容。

分数："""
        
        try:
            response = llm.generate(prompt, max_tokens=10)
            score = float(response.strip())
            return min(max(score, 0), 10)  # 限制在0-10范围
        except:
            return 5.0  # 默认分数


def create_reranker(
    model_name: Optional[str] = None,
    use_lightweight: bool = False
) -> Reranker:
    """创建重排序器
    
    Args:
        model_name: 模型名称
        use_lightweight: 是否使用轻量级（LLM）重排序器
        
    Returns:
        重排序器实例
    """
    config = get_config()
    rag_cfg = config.get_rag_config()
    
    if use_lightweight:
        return LightweightReranker()
    
    if model_name is None:
        model_name = rag_cfg.get("reranker_model", "BAAI/bge-reranker-v2-m3")
    
    return Reranker(model_name=model_name)
