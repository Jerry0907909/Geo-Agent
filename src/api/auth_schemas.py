"""认证相关的API数据模式

定义用户认证、注册、登录等接口的请求和响应模型。
"""

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field, EmailStr, validator
import re


# ==================== 用户认证模式 ====================


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, description="全名", max_length=100)
    verification_code: str = Field(..., description="邮箱验证码", min_length=6, max_length=6)

    @validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v


class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""
    email: EmailStr = Field(..., description="邮箱地址")


class UserLoginRequest(BaseModel):
    """用户登录请求（密码登录或验证码登录）"""
    username: str = Field(..., description="用户名或邮箱")
    password: Optional[str] = Field(None, description="密码（密码登录时使用）")
    verification_code: Optional[str] = Field(None, description="验证码（验证码登录时使用，6位数字）", min_length=6, max_length=6)


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(default=1800, description="过期时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    full_name: Optional[str] = Field(None, description="全名", max_length=100)
    avatar_url: Optional[str] = Field(None, description="头像URL")


class PasswordChangeRequest(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)
    confirm_password: str = Field(..., description="确认新密码", min_length=6, max_length=100)

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("两次输入的新密码不一致")
        return v


# ==================== 设置管理 ====================


class LLMConfigRequest(BaseModel):
    """LLM 配置请求"""
    provider: str = Field(..., description="提供商名称")
    base_url: str = Field(..., description="API Base URL")
    api_key: str = Field(..., description="API Key")
    model_name: str = Field(..., description="模型名称")
    temperature: Optional[float] = Field(0.7, description="温度参数", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(2048, description="最大 Token 数", ge=1, le=128000)


class LLMConfigResponse(BaseModel):
    """LLM 配置响应"""
    provider: str
    base_url: str
    api_key: str
    model_name: str
    temperature: float
    max_tokens: int


# ==================== 会话管理模式 ====================


class ConversationCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, description="会话标题", max_length=200)


class ConversationResponse(BaseModel):
    """会话响应"""
    id: int = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    summary: Optional[str] = Field(None, description="会话摘要")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    total: int = Field(..., description="总数")
    conversations: List[ConversationResponse] = Field(default_factory=list, description="会话列表")


class ConversationUpdateRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, description="会话标题", max_length=200)


# ==================== 消息管理模式 ====================


class MessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容", min_length=1, max_length=10000)
    conversation_id: Optional[int] = Field(None, description="会话ID，不提供则创建新会话")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="角色 (user/assistant/system)")
    content: str = Field(..., description="消息内容")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据", serialization_alias="metadata")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    conversation_id: Optional[int] = Field(None, description="会话ID，不提供则创建新会话")
    mode: str = Field(
        default="chat",
        description="对话模式: chat(普通对话), rag(知识库检索)"
    )
    top_k: int = Field(default=5, description="检索文档数量", ge=1, le=10)
    min_relevance_score: float = Field(default=0.0, description="最小相关度阈值 (0.0-1.0)", ge=0.0, le=1.0)
    web_search: bool = Field(default=False, description="是否启用网络搜索")
    return_sources: bool = Field(default=True, description="是否返回参考来源")
    image_base64: Optional[str] = Field(None, description="图像的Base64编码数据")
    model_name: Optional[str] = Field(None, description="指定使用的模型名称，为空则使用用户已保存的 LLM 配置")
    
    @validator("mode")
    def validate_mode(cls, v):
        allowed = ["chat", "rag"]
        if v not in allowed:
            raise ValueError(f"模式必须是 {allowed} 之一")
        return v


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: int = Field(..., description="会话ID")
    message_id: int = Field(..., description="消息ID")
    answer: str = Field(..., description="AI回答")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="参考来源")
    reasoning_steps: List[Dict[str, Any]] = Field(default_factory=list, description="推理步骤")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")


class MessageListResponse(BaseModel):
    """消息列表响应"""
    conversation_id: int = Field(..., description="会话ID")
    messages: List[MessageResponse] = Field(default_factory=list, description="消息列表")
    total: int = Field(..., description="消息总数")


# ==================== 用户偏好设置模式 ====================


class UserPreferenceResponse(BaseModel):
    """用户偏好响应"""
    language: str = Field(default="zh-CN", description="语言")
    theme: str = Field(default="light", description="主题")
    default_model: Optional[str] = Field(None, description="默认模型")
    max_context_messages: int = Field(default=10, description="上下文消息数")
    enable_memory: bool = Field(default=True, description="是否启用记忆")
    settings: Optional[Dict[str, Any]] = Field(None, description="其他设置")
    
    class Config:
        from_attributes = True


class UserPreferenceUpdateRequest(BaseModel):
    """用户偏好更新请求"""
    language: Optional[str] = Field(None, description="语言")
    theme: Optional[str] = Field(None, description="主题")
    default_model: Optional[str] = Field(None, description="默认模型")
    max_context_messages: Optional[int] = Field(None, description="上下文消息数", ge=1, le=50)
    enable_memory: Optional[bool] = Field(None, description="是否启用记忆")
    settings: Optional[Dict[str, Any]] = Field(None, description="其他设置")


# ==================== 搜索历史模式 ====================


class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""
    id: int = Field(..., description="记录ID")
    query: str = Field(..., description="搜索查询")
    result_count: Optional[int] = Field(None, description="结果数量")
    search_type: str = Field(..., description="搜索类型")
    response_time: Optional[int] = Field(None, description="响应时间(ms)")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class SearchHistoryListResponse(BaseModel):
    """搜索历史列表响应"""
    total: int = Field(..., description="总数")
    history: List[SearchHistoryResponse] = Field(default_factory=list, description="历史记录")
