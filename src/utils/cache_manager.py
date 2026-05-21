"""缓存管理器

实现多级缓存系统，提高查询性能。
支持内存缓存、Redis缓存。
"""

from typing import Optional, List, Any, Callable
import hashlib
import pickle
import logging
import time
from functools import wraps
from datetime import timedelta

from cachetools import TTLCache, LRUCache

from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 全局缓存实例
_cache_manager: Optional["CacheManager"] = None


class CacheManager:
    """多级缓存管理器
    
    L1: 内存缓存 (TTLCache)
    L2: Redis缓存 (可选)
    """
    
    def __init__(
        self,
        memory_cache_size: int = 1000,
        ttl_seconds: int = 3600,
        redis_host: Optional[str] = None,
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None
    ):
        """初始化缓存管理器
        
        Args:
            memory_cache_size: 内存缓存大小
            ttl_seconds: 缓存过期时间（秒）
            redis_host: Redis主机地址，为None则不使用Redis
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码
        """
        self.ttl_seconds = ttl_seconds
        
        # L1: 内存缓存
        self._embedding_cache = TTLCache(maxsize=memory_cache_size, ttl=ttl_seconds)
        self._query_cache = TTLCache(maxsize=memory_cache_size // 2, ttl=ttl_seconds)
        self._general_cache = TTLCache(maxsize=memory_cache_size, ttl=ttl_seconds)
        
        # L2: Redis缓存（可选）
        self.redis = None
        if redis_host:
            try:
                import redis
                self.redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=False
                )
                # 测试连接
                self.redis.ping()
                logger.info(f"Redis缓存连接成功: {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"Redis连接失败，将只使用内存缓存: {e}")
                self.redis = None
        
        # 统计
        self._hits = 0
        self._misses = 0
    
    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键
        
        Args:
            prefix: 缓存前缀
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            缓存键字符串
        """
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    # ==================== Embedding缓存 ====================
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取向量缓存
        
        Args:
            text: 文本
            
        Returns:
            缓存的向量，未命中返回None
        """
        key = self._get_cache_key("emb", text)
        
        # L1: 内存缓存
        if key in self._embedding_cache:
            self._hits += 1
            return self._embedding_cache[key]
        
        # L2: Redis缓存
        if self.redis:
            try:
                cached = self.redis.get(key)
                if cached:
                    embedding = pickle.loads(cached)
                    # 回写到L1
                    self._embedding_cache[key] = embedding
                    self._hits += 1
                    return embedding
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        self._misses += 1
        return None
    
    def set_embedding(self, text: str, embedding: List[float]) -> None:
        """设置向量缓存
        
        Args:
            text: 文本
            embedding: 向量
        """
        key = self._get_cache_key("emb", text)
        
        # L1: 内存缓存
        self._embedding_cache[key] = embedding
        
        # L2: Redis缓存
        if self.redis:
            try:
                self.redis.setex(
                    key,
                    timedelta(seconds=self.ttl_seconds),
                    pickle.dumps(embedding)
                )
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
    
    # ==================== 查询结果缓存 ====================
    
    def get_query_result(self, query: str, **params) -> Optional[Any]:
        """获取查询结果缓存
        
        Args:
            query: 查询文本
            **params: 查询参数
            
        Returns:
            缓存的结果，未命中返回None
        """
        key = self._get_cache_key("query", query, **params)
        
        # L1: 内存缓存
        if key in self._query_cache:
            self._hits += 1
            return self._query_cache[key]
        
        # L2: Redis缓存
        if self.redis:
            try:
                cached = self.redis.get(key)
                if cached:
                    result = pickle.loads(cached)
                    self._query_cache[key] = result
                    self._hits += 1
                    return result
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        self._misses += 1
        return None
    
    def set_query_result(self, query: str, result: Any, ttl: Optional[int] = None, **params) -> None:
        """设置查询结果缓存
        
        Args:
            query: 查询文本
            result: 查询结果
            ttl: 过期时间（秒），默认使用全局设置
            **params: 查询参数
        """
        key = self._get_cache_key("query", query, **params)
        ttl = ttl or self.ttl_seconds
        
        # L1: 内存缓存
        self._query_cache[key] = result
        
        # L2: Redis缓存
        if self.redis:
            try:
                self.redis.setex(
                    key,
                    timedelta(seconds=ttl),
                    pickle.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
    
    # ==================== 通用缓存 ====================
    
    def get(self, key: str) -> Optional[Any]:
        """获取通用缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，未命中返回None
        """
        if key in self._general_cache:
            self._hits += 1
            return self._general_cache[key]
        
        if self.redis:
            try:
                cached = self.redis.get(f"gen:{key}")
                if cached:
                    value = pickle.loads(cached)
                    self._general_cache[key] = value
                    self._hits += 1
                    return value
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置通用缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        ttl = ttl or self.ttl_seconds
        
        self._general_cache[key] = value
        
        if self.redis:
            try:
                self.redis.setex(
                    f"gen:{key}",
                    timedelta(seconds=ttl),
                    pickle.dumps(value)
                )
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
    
    def delete(self, key: str) -> None:
        """删除缓存
        
        Args:
            key: 缓存键
        """
        if key in self._general_cache:
            del self._general_cache[key]
        
        if self.redis:
            try:
                self.redis.delete(f"gen:{key}")
            except Exception as e:
                logger.warning(f"Redis删除失败: {e}")
    
    # ==================== 缓存管理 ====================
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self._embedding_cache.clear()
        self._query_cache.clear()
        self._general_cache.clear()
        
        if self.redis:
            try:
                self.redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis清空失败: {e}")
        
        logger.info("所有缓存已清空")
    
    def get_stats(self) -> dict:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2%}",
            "embedding_cache_size": len(self._embedding_cache),
            "query_cache_size": len(self._query_cache),
            "general_cache_size": len(self._general_cache),
            "redis_connected": self.redis is not None
        }


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器
    
    Returns:
        CacheManager 实例
    """
    global _cache_manager
    
    if _cache_manager is None:
        config = get_config()
        cache_cfg = config.raw_config.get("cache", {})
        
        _cache_manager = CacheManager(
            memory_cache_size=cache_cfg.get("cache_max_size", 1000),
            ttl_seconds=cache_cfg.get("cache_ttl", 3600),
            redis_host=cache_cfg.get("redis_host"),
            redis_port=cache_cfg.get("redis_port", 6379),
            redis_db=cache_cfg.get("redis_db", 0),
            redis_password=cache_cfg.get("redis_password")
        )
    
    return _cache_manager


def cached(ttl: int = 3600, key_prefix: str = "func"):
    """缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 生成缓存键
            key = cache._get_cache_key(
                f"{key_prefix}:{func.__name__}",
                *args,
                **kwargs
            )
            
            # 尝试获取缓存
            result = cache.get(key)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


class CachedEmbeddingProvider:
    """带缓存的向量提供者
    
    包装现有的EmbeddingProvider，添加缓存功能。
    """
    
    def __init__(self, base_provider, cache: Optional[CacheManager] = None):
        """初始化
        
        Args:
            base_provider: 基础向量提供者
            cache: 缓存管理器
        """
        self.base_provider = base_provider
        self.cache = cache or get_cache_manager()
    
    def embed_text(self, text: str) -> List[float]:
        """获取文本向量（带缓存）
        
        Args:
            text: 输入文本
            
        Returns:
            向量
        """
        # 尝试从缓存获取
        cached = self.cache.get_embedding(text)
        if cached is not None:
            return cached
        
        # 计算向量
        embedding = self.base_provider.embed_text(text)
        
        # 存入缓存
        self.cache.set_embedding(text, embedding)
        
        return embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量（带缓存）
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # 检查缓存
        for idx, text in enumerate(texts):
            cached = self.cache.get_embedding(text)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(idx)
        
        # 批量计算未缓存的向量
        if uncached_texts:
            new_embeddings = self.base_provider.embed_batch(uncached_texts)
            for idx, embedding in zip(uncached_indices, new_embeddings):
                results[idx] = embedding
                self.cache.set_embedding(texts[idx], embedding)
        
        return results
    
    # 代理其他属性和方法
    def __getattr__(self, name):
        return getattr(self.base_provider, name)
