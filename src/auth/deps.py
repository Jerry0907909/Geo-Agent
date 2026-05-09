"""认证依赖项

提供FastAPI依赖注入的认证函数。
"""

from typing import Optional
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.auth.security import validate_token
from src.database.mysql_manager import get_db
from src.database.models import User

logger = logging.getLogger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    user_id = validate_token(token, token_type="access")
    
    if user_id is None:
        raise credentials_exception
    
    # 查询用户
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        当前活跃用户
        
    Raises:
        HTTPException: 用户未激活时抛出400错误
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账号已禁用"
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取可选的当前用户（允许未登录访问）
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        用户对象或None
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    user_id = validate_token(token, token_type="access")
    
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取超级用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        超级用户
        
    Raises:
        HTTPException: 非超级用户时抛出403错误
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user
