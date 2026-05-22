"""重排序器

支持两种模式：
1. API 模式（默认）— 调用硅基流动 /v1/rerank，零本地资源消耗
2. 本地模式 — 加载 sentence-transformers CrossEncoder
"""

from typing import List, Optional, Tuple
import logging

from langchain_core.documents import Document
from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 本地模型全局缓存
_reranker_model = None


class SiliconFlowReranker:
    """基于硅基流动 API 的重排序器（推荐，无需本地 GPU）"""

    def __init__(
        self,
        api_endpoint: str = "https://api.siliconflow.cn/v1/rerank",
        api_key: str = "",
        model_name: str = "BAAI/bge-reranker-v2-m3",
    ):
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name

    def rerank(
        self, query: str, documents: List[Document], top_k: Optional[int] = None,
    ) -> List[Document]:
        if not documents:
            return []
        if top_k is None:
            top_k = len(documents)

        import httpx
        texts = [doc.page_content for doc in documents]

        try:
            with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
                resp = client.post(
                    self.api_endpoint,
                    json={
                        "model": self.model_name,
                        "query": query,
                        "documents": texts,
                        "top_n": top_k,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("[Rerank API] 调用失败: %s，返回原始排序", e)
            return documents[:top_k]

        results = data.get("results", [])
        ranked = []
        for r in results:
            idx = r.get("index", 0)
            score = r.get("relevance_score", 0.0)
            if idx < len(documents):
                doc = documents[idx]
                doc.metadata["rerank_score"] = float(score)
                ranked.append(doc)
        logger.info("[Rerank API] %d docs → top_%d", len(documents), len(ranked))
        return ranked[:top_k]

    def score(self, query: str, document: str) -> float:
        docs = [Document(page_content=document)]
        ranked = self.rerank(query, docs, top_k=1)
        if ranked:
            return float(ranked[0].metadata.get("rerank_score", 0.0))
        return 0.0


class Reranker:
    """本地交叉编码器重排序器（备选方案）"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
        use_fp16: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None

    @property
    def model(self):
        global _reranker_model
        if self._model is not None:
            return self._model
        if _reranker_model is not None:
            self._model = _reranker_model
            return self._model

        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, device=self.device, max_length=512)
            _reranker_model = self._model
            logger.info("[Reranker] 本地模型加载完成: %s", self.model_name)
            return self._model
        except ImportError:
            logger.error("sentence-transformers 未安装")
            raise
        except Exception as e:
            logger.error("[Reranker] 模型加载失败: %s", e)
            raise

    def rerank(self, query: str, documents: List[Document], top_k: Optional[int] = None) -> List[Document]:
        if not documents:
            return []
        if top_k is None:
            top_k = len(documents)
        try:
            pairs = [(query, doc.page_content) for doc in documents]
            scores = self.model.predict(pairs, show_progress_bar=False)
            pairs_with_scores = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
            result = []
            for doc, score in pairs_with_scores[:top_k]:
                doc.metadata["rerank_score"] = float(score)
                result.append(doc)
            return result
        except Exception as e:
            logger.error("[Reranker] 重排序失败: %s", e)
            return documents[:top_k]

    def score(self, query: str, document: str) -> float:
        try:
            return float(self.model.predict([(query, document)])[0])
        except Exception:
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
    use_lightweight: bool = False,
) -> "SiliconFlowReranker | Reranker | LightweightReranker":
    """创建重排序器（优先使用硅基流动 API）

    Args:
        model_name: 模型名称（默认从 config 读取）
        use_lightweight: 是否使用 LLM 重排序器
    """
    if use_lightweight:
        return LightweightReranker()

    config = get_config()
    rag_cfg = config.get_rag_config()

    if model_name is None:
        model_name = rag_cfg.get("reranker_model", "BAAI/bge-reranker-v2-m3")

    # API 模式优先
    use_api = rag_cfg.get("reranker_api", True)
    if use_api:
        api_endpoint = rag_cfg.get("reranker_api_endpoint", "https://api.siliconflow.cn/v1/rerank")
        api_key = config.get("llm.api_key") or config.get("embedding.api_key")
        if api_key:
            logger.info("[Reranker] 使用硅基流动 API: %s (%s)", api_endpoint, model_name)
            return SiliconFlowReranker(
                api_endpoint=api_endpoint,
                api_key=api_key,
                model_name=model_name,
            )

    logger.info("[Reranker] API key 未配置，使用本地模型: %s", model_name)
    return Reranker(model_name=model_name)
