"""验证码管理 - 生成、存储、验证邮箱验证码

优先使用 Redis 存储（进程重启后数据不丢失），Redis 不可用时回退到内存字典。
"""

import random
import time
import json
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# { email: (code, expires_at_timestamp) } — 仅 Redis 不可用时使用
_codes: Dict[str, Tuple[str, float]] = {}
_last_send_time: Dict[str, float] = {}

CODE_LENGTH = 6
CODE_TTL_SECONDS = 300  # 5 分钟
RESEND_COOLDOWN_SECONDS = 60  # 重发间隔

# Redis 客户端（延迟初始化）
_redis: Optional[object] = None
_redis_available: Optional[bool] = None


def _get_redis():
    """获取 Redis 客户端（延迟连接）"""
    global _redis, _redis_available
    if _redis_available is not None:
        return _redis if _redis_available else None

    from src.utils.config import get_config
    config = get_config()
    cache_cfg = config.config.get("cache", {})
    redis_host = cache_cfg.get("redis_host")

    if not redis_host:
        _redis_available = False
        return None

    try:
        import redis
        _redis = redis.Redis(
            host=redis_host,
            port=int(cache_cfg.get("redis_port", 6379)),
            db=int(cache_cfg.get("redis_db", 0)),
            password=cache_cfg.get("redis_password") or None,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        _redis.ping()
        _redis_available = True
        logger.info("验证码存储: Redis 已连接")
        return _redis
    except Exception as e:
        logger.warning("Redis 不可用，验证码使用内存存储: %s", e)
        _redis_available = False
        return None


def _redis_key(email: str) -> str:
    return f"verification:code:{email}"


def _redis_cooldown_key(email: str) -> str:
    return f"verification:cooldown:{email}"


def generate_code() -> str:
    """生成 6 位数字验证码"""
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


def store_code(email: str, code: str) -> None:
    r = _get_redis()
    if r:
        pipe = r.pipeline()
        pipe.setex(_redis_key(email), CODE_TTL_SECONDS, code)
        pipe.setex(_redis_cooldown_key(email), RESEND_COOLDOWN_SECONDS, "1")
        pipe.execute()
    else:
        _codes[email] = (code, time.time() + CODE_TTL_SECONDS)
        _last_send_time[email] = time.time()


def verify_code(email: str, code: str) -> bool:
    """验证码是否匹配且未过期，验证成功后删除"""
    r = _get_redis()
    if r:
        key = _redis_key(email)
        stored = r.get(key)
        if stored is None:
            return False
        if stored != code:
            return False
        r.delete(key, _redis_cooldown_key(email))
        return True

    entry = _codes.get(email)
    if entry is None:
        return False
    stored_code, expires_at = entry
    if time.time() > expires_at:
        del _codes[email]
        return False
    if stored_code != code:
        return False
    del _codes[email]
    _last_send_time.pop(email, None)
    return True


def can_resend(email: str) -> Tuple[bool, int]:
    """检查是否可以重新发送，返回 (可重发, 剩余等待秒数)"""
    r = _get_redis()
    if r:
        ttl = r.ttl(_redis_cooldown_key(email))
        if ttl > 0:
            return False, ttl
        return True, 0

    last = _last_send_time.get(email)
    if last is None:
        return True, 0
    elapsed = time.time() - last
    if elapsed >= RESEND_COOLDOWN_SECONDS:
        return True, 0
    return False, int(RESEND_COOLDOWN_SECONDS - elapsed)


def cleanup_expired() -> int:
    """清理过期验证码（仅内存存储时需要，Redis 自动过期）"""
    if _get_redis():
        return 0
    now = time.time()
    expired = [email for email, (_, expires) in _codes.items() if now > expires]
    for email in expired:
        del _codes[email]
    if expired:
        logger.info("清理了 %d 条过期验证码", len(expired))
    return len(expired)
