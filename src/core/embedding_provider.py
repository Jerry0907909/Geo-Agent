"""Embedding Provider - 基于 LangChain 的词向量模型接口

使用 LangChain Embeddings 实现，支持 OpenAI 兼容 API。
"""

from __future__ import annotations

from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from src.utils.config import get_config
from src.core.http_client_factory import create_http_clients


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
        use_env_proxy: bool = False,
        proxy_url: Optional[str] = None,
        max_retries: int = 0,
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
        self.use_env_proxy = use_env_proxy
        self.proxy_url = proxy_url
        self.max_retries = max_retries
        
        # 提取 base_url
        base_url = self._get_base_url()
        http_client, http_async_client = create_http_clients(
            timeout=float(timeout),
            use_env_proxy=use_env_proxy,
            proxy_url=proxy_url,
        )
        
        # 创建 LangChain OpenAIEmbeddings 实例
        # tiktoken_enabled=False 避免下载 tiktoken 编码文件（网络受限环境）
        self._embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            timeout=float(timeout),
            dimensions=dimensions,
            max_retries=max_retries,
            http_client=http_client,
            http_async_client=http_async_client,
            tiktoken_enabled=True,  # 仍启用 tiktoken 以支持文本分割等功能，但不下载编码文件
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


def create_embedding_provider(
    use_cache: bool = True,
) -> Embeddings:
    """根据全局配置创建默认的 EmbeddingProvider 实例

    当 use_cache=True 且配置启用了 embedding 缓存时，使用 CachedEmbeddingProvider
    包装，提供 L1 内存 + L2 Redis 双层缓存。
    """
    config = get_config()
    emb_cfg = config.get_embedding_config()
    cache_cfg = config.config.get("cache", {})

    provider = emb_cfg.get("provider")
    if provider == "siliconflow":
        api_key = emb_cfg.get("api_key")
        api_endpoint = emb_cfg.get("api_endpoint")
        model_name = emb_cfg.get("model_name")
        timeout = emb_cfg.get("request_timeout", 30)
        dimensions = emb_cfg.get("embedding_dim")
        use_env_proxy = emb_cfg.get("use_env_proxy", False)
        proxy_url = emb_cfg.get("proxy_url")
        max_retries = emb_cfg.get("max_retries", 0)

        if not api_key or not api_endpoint or not model_name:
            raise ValueError("SiliconFlow embedding 配置不完整")

        base = LangChainEmbeddingProvider(
            api_key=api_key,
            api_endpoint=api_endpoint,
            model_name=model_name,
            timeout=timeout,
            dimensions=dimensions,
            use_env_proxy=use_env_proxy,
            proxy_url=proxy_url,
            max_retries=max_retries,
        )

        # 启用缓存包装
        if use_cache and cache_cfg.get("enable_embedding_cache", True):
            from src.utils.cache_manager import CachedEmbeddingProvider, get_cache_manager
            cache = get_cache_manager()
            if cache.redis or cache_cfg.get("redis_host"):
                import logging
                logging.getLogger(__name__).info(
                    "Embedding 缓存已启用 (L1 内存 + L2 Redis)"
                )
            else:
                import logging
                logging.getLogger(__name__).info(
                    "Embedding 缓存已启用 (L1 内存, Redis 未连接)"
                )
            return CachedEmbeddingProvider(base, cache=cache)

        return base

    raise ValueError(f"不支持的 embedding provider: {provider}")
