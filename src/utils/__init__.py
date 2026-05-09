"""工具模块

提供配置管理、缓存、日志等工具功能。
"""

from src.utils.config import Config, get_config, reset_config

# cache_manager 依赖可选三方包；在仅使用配置模块的场景下不应阻塞导入。
try:
    from src.utils.cache_manager import (
        CacheManager,
        get_cache_manager,
        cached,
        CachedEmbeddingProvider,
    )
except ModuleNotFoundError:  # pragma: no cover - 取决于本地环境依赖是否齐全
    CacheManager = None
    get_cache_manager = None
    cached = None
    CachedEmbeddingProvider = None

__all__ = [
    # 配置
    "Config",
    "get_config",
    "reset_config",
    # 缓存
    "CacheManager",
    "get_cache_manager",
    "cached",
    "CachedEmbeddingProvider",
]
