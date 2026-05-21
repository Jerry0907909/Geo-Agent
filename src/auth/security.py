"""安全工具模块

提供密码哈希、JWT令牌创建和验证等功能。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import logging
import os

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_auth_config() -> Dict[str, Any]:
    """获取认证配置"""
    config = get_config()
    auth_cfg = config.raw_config.get("auth", {})
    
    return {
        "secret_key": auth_cfg.get("secret_key") or os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production"),
        "algorithm": auth_cfg.get("algorithm", "HS256"),
        "access_token_expire_minutes": auth_cfg.get("access_token_expire_minutes", 30),
        "refresh_token_expire_days": auth_cfg.get("refresh_token_expire_days", 7),
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT访问令牌
    """
    auth_cfg = get_auth_config()
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=auth_cfg["access_token_expire_minutes"])
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        auth_cfg["secret_key"],
        algorithm=auth_cfg["algorithm"]
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建刷新令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT刷新令牌
    """
    auth_cfg = get_auth_config()
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=auth_cfg["refresh_token_expire_days"])
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        auth_cfg["secret_key"],
        algorithm=auth_cfg["algorithm"]
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码JWT令牌
    
    Args:
        token: JWT令牌
        
    Returns:
        解码后的数据，失败返回None
    """
    auth_cfg = get_auth_config()
    
    try:
        payload = jwt.decode(
            token,
            auth_cfg["secret_key"],
            algorithms=[auth_cfg["algorithm"]]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT解码失败: {e}")
        return None


def create_tokens(user_id: int, username: str) -> Dict[str, str]:
    """创建访问令牌和刷新令牌
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        包含access_token和refresh_token的字典
    """
    token_data = {"sub": str(user_id), "username": username}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def validate_token(token: str, token_type: str = "access") -> Optional[int]:
    """验证令牌并返回用户ID
    
    Args:
        token: JWT令牌
        token_type: 令牌类型 ("access" 或 "refresh")
        
    Returns:
        用户ID，验证失败返回None
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # 检查令牌类型
    if payload.get("type") != token_type:
        logger.warning(f"令牌类型不匹配: 期望 {token_type}, 实际 {payload.get('type')}")
        return None
    
    # 获取用户ID
    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None
    
    try:
        return int(user_id_str)
    except ValueError:
        return None
