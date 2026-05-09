"""数据库模型定义

定义用户、会话、消息等数据模型，支持MySQL存储。
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, Index, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    # 关联
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Conversation(Base):
    """会话模型"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=True)  # 会话标题，可自动生成
    summary = Column(Text, nullable=True)  # 会话摘要
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # 存储额外信息，如来源、推理步骤等
    tokens_used = Column(Integer, nullable=True)  # Token消耗记录
    created_at = Column(DateTime, default=func.now())

    # 关联
    conversation = relationship("Conversation", back_populates="messages")

    # 索引优化
    __table_args__ = (
        Index("idx_conversation_created", "conversation_id", "created_at"),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class UserPreference(Base):
    """用户偏好设置"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    language = Column(String(10), default="zh-CN")
    theme = Column(String(20), default="light")
    default_model = Column(String(50), nullable=True)
    max_context_messages = Column(Integer, default=10)  # 上下文窗口大小
    enable_memory = Column(Boolean, default=True)
    settings = Column(JSON, nullable=True)  # 其他自定义设置
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id})>"


class SearchHistory(Base):
    """搜索历史记录"""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    result_count = Column(Integer, nullable=True)
    search_type = Column(String(20), default="rag")  # rag, agent, hybrid
    response_time = Column(Integer, nullable=True)  # 响应时间（毫秒）
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_user_search_time", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id})>"


class DocumentAccess(Base):
    """文档访问记录"""
    __tablename__ = "document_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(100), nullable=False, index=True)
    document_name = Column(String(255), nullable=True)
    access_type = Column(String(20), default="view")  # view, download, cite
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_user_doc_access", "user_id", "document_id"),
    )

    def __repr__(self):
        return f"<DocumentAccess(user_id={self.user_id}, document_id={self.document_id})>"


class CustomAgent(Base):
    """自定义AI助手模型
    
    用户可以创建自定义的AI助手，包含：
    - 自定义名称和描述
    - 系统提示词（指令）
    - 温度参数（控制回答风格）
    - 专属知识库
    """
    __tablename__ = "custom_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # 助手名称
    description = Column(Text, nullable=True)  # 助手描述/用途说明
    system_prompt = Column(Text, nullable=False)  # 系统提示词/指令
    temperature = Column(Integer, default=50)  # 温度 0-100，映射到 0.0-1.0
    icon = Column(String(50), default="bot")  # 图标标识
    color = Column(String(20), default="#6366f1")  # 主题色
    collection_name = Column(String(100), nullable=True)  # 专属知识库集合名称
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # 是否公开分享
    use_count = Column(Integer, default=0)  # 使用次数统计
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联
    user = relationship("User", backref="custom_agents")

    __table_args__ = (
        Index("idx_user_agent", "user_id", "is_active"),
    )

    def __repr__(self):
        return f"<CustomAgent(id={self.id}, name={self.name}, user_id={self.user_id})>"
