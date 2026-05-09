"""Embedding Provider - 基于 LangChain 的词向量模型接口

使用 LangChain Embeddings 实现，支持 OpenAI 兼容 API。
"""

from __future__ import annotations

from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from src.utils.config import get_config


class LangChainEmbeddingProvider(Embeddings):
    """基于 LangChain OpenAIEmbeddings 的实现
    
    支持 OpenAI 兼容的 Embeddings API（如 SiliconFlow）。
    继承 LangChain Embeddings 基类，可直接用于 LangChain 生态。
    """

    def __init__(
        self,
        api_key: str,
        api_endpoint: str,
        model_name: str,
        timeout: int = 30,
        dimensions: Optional[int] = None,
    ) -> None:
        """初始化 Embedding Provider
        
        Args:
            api_key: API 密钥
            api_endpoint: API 端点
            model_name: 模型名称
            timeout: 请求超时时间
            dimensions: 向量维度（可选）
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.dimensions = dimensions
        
        # 提取 base_url
        base_url = self._get_base_url()
        
        # 创建 LangChain OpenAIEmbeddings 实例
        self._embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout=float(timeout),
            dimensions=dimensions,
        )
    
    def _get_base_url(self) -> str:
        """从完整 endpoint 提取 base_url"""
        endpoint = self.api_endpoint
        # 移除常见后缀
        for suffix in ["/embeddings", "/v1/embeddings"]:
            if endpoint.endswith(suffix):
                endpoint = endpoint[:-len(suffix)]
                break
        # 确保以 /v1 结尾
        if not endpoint.endswith("/v1"):
            endpoint = endpoint.rstrip("/") + "/v1"
        return endpoint

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """对多个文档文本进行向量化
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        if not texts:
            return []
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """对单个查询文本进行向量化
        
        Args:
            text: 查询文本
            
        Returns:
            向量
        """
        return self._embeddings.embed_query(text)
    
    # 兼容旧接口
    def embed_text(self, text: str) -> List[float]:
        """对单个文本编码为向量（兼容旧接口）"""
        return self.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """对多个文本批量编码为向量（兼容旧接口）"""
        return self.embed_documents(texts)


# 保留旧类名作为别名
SiliconFlowEmbeddingProvider = LangChainEmbeddingProvider
EmbeddingProvider = LangChainEmbeddingProvider


def create_embedding_provider() -> LangChainEmbeddingProvider:
    """根据全局配置创建默认的 EmbeddingProvider 实例"""
    config = get_config()
    emb_cfg = config.get_embedding_config()

    provider = emb_cfg.get("provider")
    if provider == "siliconflow":
        api_key = emb_cfg.get("api_key")
        api_endpoint = emb_cfg.get("api_endpoint")
        model_name = emb_cfg.get("model_name")
        timeout = emb_cfg.get("request_timeout", 30)
        dimensions = emb_cfg.get("embedding_dim")

        if not api_key or not api_endpoint or not model_name:
            raise ValueError("SiliconFlow embedding 配置不完整")

        return LangChainEmbeddingProvider(
            api_key=api_key,
            api_endpoint=api_endpoint,
            model_name=model_name,
            timeout=timeout,
            dimensions=dimensions,
        )

    raise ValueError(f"不支持的 embedding provider: {provider}")
