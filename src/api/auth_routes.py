"""认证相关API路由

提供用户注册、登录、信息管理等接口。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth_schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserUpdateRequest,
    PasswordChangeRequest,
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
    SearchHistoryListResponse,
    SearchHistoryResponse,
    SendVerificationCodeRequest,
)
from src.auth.security import (
    get_password_hash,
    verify_password,
    create_tokens,
    validate_token,
)
from src.auth.deps import get_current_active_user, get_db
from src.auth.verification import generate_code, store_code, verify_code, can_resend
from src.utils.email_sender import get_email_sender
from src.database.models import User, UserPreference, SearchHistory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


# ==================== 验证码相关 ====================


@router.post("/send-verification-code")
async def send_verification_code(request: SendVerificationCodeRequest):
    """发送邮箱验证码

    用于注册和登录验证。60 秒内不可重复发送。
    """
    # 检查重发冷却
    can, wait_seconds = can_resend(request.email)
    if not can:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请 {wait_seconds} 秒后再试",
        )

    email_sender = get_email_sender()
    if not email_sender.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="邮件服务未配置，请联系管理员",
        )

    code = generate_code()
    if email_sender.send_verification_code(request.email, code):
        store_code(request.email, code)
        logger.info("验证码已发送到 %s", request.email)
        return {"message": "验证码已发送", "email": request.email}

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="验证码发送失败，请稍后重试",
    )


# ==================== 用户认证 ====================


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """用户注册

    需要先通过 /auth/send-verification-code 获取邮箱验证码。
    """
    # 先验证邮箱验证码
    if not verify_code(request.email, request.verification_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册",
        )

    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    # 创建用户
    hashed_password = get_password_hash(request.password)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
    )
    db.add(user)
    db.flush()

    preference = UserPreference(user_id=user.id)
    db.add(preference)

    db.commit()
    db.refresh(user)

    logger.info("新用户注册: %s (%s)", user.username, user.email)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """用户登录

    支持两种方式：
    - 密码登录：提供 username + password
    - 验证码登录：提供 username（邮箱） + verification_code
    """
    # 查找用户（支持用户名或邮箱）
    user = db.query(User).filter(
        (User.username == request.username) | (User.email == request.username)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证码登录
    if request.verification_code:
        if not verify_code(user.email, request.verification_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码错误或已过期",
            )
    # 密码登录
    elif request.password:
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供密码或验证码",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    user.last_login = datetime.now()
    db.commit()

    tokens = create_tokens(user.id, user.username)

    logger.info("用户登录: %s", user.username)
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新访问令牌
    
    使用刷新令牌获取新的访问令牌。
    
    Args:
        request: 刷新令牌请求
        db: 数据库会话
        
    Returns:
        新的访问令牌
    """
    user_id = validate_token(request.refresh_token, token_type="refresh")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的刷新令牌"
        )
    
    # 查找用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 创建新令牌
    tokens = create_tokens(user.id, user.username)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """用户登出
    
    客户端应删除本地存储的令牌。
    
    Returns:
        登出成功消息
    """
    logger.info(f"用户登出: {current_user.username}")
    return {"message": "登出成功"}


# ==================== 用户信息管理 ====================


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息
    
    Returns:
        当前用户信息
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息
    
    Args:
        request: 更新请求
        
    Returns:
        更新后的用户信息
    """
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码
    
    Args:
        request: 密码修改请求
        
    Returns:
        修改成功消息
    """
    # 验证旧密码
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # 验证新密码与确认密码一致（schema 层已校验，此处二次确认）
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的新密码不一致",
        )

    # 更新密码
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    logger.info(f"用户修改密码: {current_user.username}")
    return {"message": "密码修改成功"}


# ==================== 用户偏好设置 ====================


@router.get("/preferences", response_model=UserPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户偏好设置
    
    Returns:
        用户偏好设置
    """
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        # 创建默认偏好
        preference = UserPreference(user_id=current_user.id)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    
    return preference


@router.put("/preferences", response_model=UserPreferenceResponse)
async def update_preferences(
    request: UserPreferenceUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户偏好设置
    
    Args:
        request: 偏好更新请求
        
    Returns:
        更新后的偏好设置
    """
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        preference = UserPreference(user_id=current_user.id)
        db.add(preference)
    
    # 更新字段
    if request.language is not None:
        preference.language = request.language
    if request.theme is not None:
        preference.theme = request.theme
    if request.default_model is not None:
        preference.default_model = request.default_model
    if request.max_context_messages is not None:
        preference.max_context_messages = request.max_context_messages
    if request.enable_memory is not None:
        preference.enable_memory = request.enable_memory
    if request.settings is not None:
        preference.settings = request.settings
    
    db.commit()
    db.refresh(preference)
    
    return preference


# ==================== 搜索历史 ====================


@router.get("/search-history", response_model=SearchHistoryListResponse)
async def get_search_history(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取搜索历史
    
    Args:
        limit: 返回数量限制
        
    Returns:
        搜索历史列表
    """
    history = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return SearchHistoryListResponse(
        total=len(history),
        history=[SearchHistoryResponse.model_validate(h) for h in history]
    )


@router.delete("/search-history")
async def clear_search_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """清空搜索历史
    
    Returns:
        清空成功消息
    """
    db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).delete()
    db.commit()
    
    return {"message": "搜索历史已清空"}
