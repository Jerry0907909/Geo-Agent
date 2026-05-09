"""MySQL 数据库连接管理

提供数据库连接、会话管理和初始化功能。
"""

from contextlib import contextmanager
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.database.models import Base
from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """获取数据库连接URL"""
    config = get_config()
    db_cfg = config.get_database_config()
    
    # MySQL连接参数
    host = db_cfg.get("mysql_host", "localhost")
    port = db_cfg.get("mysql_port", 3306)
    user = db_cfg.get("mysql_user", "root")
    password = db_cfg.get("mysql_password", "")
    database = db_cfg.get("mysql_database", "geology_agent")
    charset = db_cfg.get("mysql_charset", "utf8mb4")
    
    # 构建连接URL
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
    return url


def get_engine():
    """获取或创建数据库引擎"""
    global _engine
    
    if _engine is None:
        database_url = get_database_url()
        
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,  # 30分钟回收连接
            pool_pre_ping=True,  # 连接健康检查
            echo=False,  # 设为True可查看SQL语句
        )
        logger.info("MySQL数据库引擎创建成功")
    
    return _engine


def get_session_local():
    """获取会话工厂"""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（用于依赖注入）
    
    Yields:
        数据库会话对象
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话（上下文管理器版本）
    
    用于非FastAPI的场景，如后台任务。
    
    Yields:
        数据库会话对象
    """
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话错误: {e}")
        raise
    finally:
        session.close()


def init_database(drop_all: bool = False):
    """初始化数据库
    
    Args:
        drop_all: 是否删除所有表后重建
    """
    engine = get_engine()
    
    try:
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
        
        # 创建表
        if drop_all:
            logger.warning("即将删除所有数据库表...")
            Base.metadata.drop_all(bind=engine)
            logger.info("所有表已删除")
        
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建/更新成功")
        
        return True
    
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def check_database_connection() -> bool:
    """检查数据库连接状态
    
    Returns:
        连接是否正常
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False


def close_database():
    """关闭数据库连接"""
    global _engine, _SessionLocal
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("数据库连接已关闭")


class MySQLManager:
    """MySQL数据库管理器
    
    提供用户、会话、消息的CRUD操作。
    """
    
    def __init__(self, session: Optional[Session] = None):
        """初始化管理器
        
        Args:
            session: 可选的数据库会话
        """
        self._session = session
        self._own_session = session is None
    
    @property
    def session(self) -> Session:
        """获取数据库会话"""
        if self._session is None:
            SessionLocal = get_session_local()
            self._session = SessionLocal()
        return self._session
    
    def close(self):
        """关闭会话"""
        if self._own_session and self._session is not None:
            self._session.close()
            self._session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.close()
    
    # ==================== 用户操作 ====================
    
    def create_user(self, username: str, email: str, hashed_password: str, 
                    full_name: Optional[str] = None) -> "User":
        """创建用户"""
        from src.database.models import User, UserPreference
        
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name
        )
        self.session.add(user)
        self.session.flush()  # 获取用户ID
        
        # 创建默认偏好设置
        preference = UserPreference(user_id=user.id)
        self.session.add(preference)
        
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional["User"]:
        """根据ID获取用户"""
        from src.database.models import User
        return self.session.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional["User"]:
        """根据用户名获取用户"""
        from src.database.models import User
        return self.session.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional["User"]:
        """根据邮箱获取用户"""
        from src.database.models import User
        return self.session.query(User).filter(User.email == email).first()
    
    def update_user_last_login(self, user_id: int):
        """更新用户最后登录时间"""
        from src.database.models import User
        from datetime import datetime
        
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now()
            self.session.commit()
    
    # ==================== 会话操作 ====================
    
    def create_conversation(self, user_id: int, title: Optional[str] = None) -> "Conversation":
        """创建新会话"""
        from src.database.models import Conversation
        
        conversation = Conversation(user_id=user_id, title=title or "新对话")
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation
    
    def get_conversation(self, conversation_id: int) -> Optional["Conversation"]:
        """获取会话"""
        from src.database.models import Conversation
        return self.session.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    def get_user_conversations(self, user_id: int, limit: int = 20, offset: int = 0) -> list:
        """获取用户的所有会话"""
        from src.database.models import Conversation
        
        return (
            self.session.query(Conversation)
            .filter(Conversation.user_id == user_id, Conversation.is_active == True)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def update_conversation_title(self, conversation_id: int, title: str):
        """更新会话标题"""
        conv = self.get_conversation(conversation_id)
        if conv:
            conv.title = title
            self.session.commit()
    
    def delete_conversation(self, conversation_id: int):
        """删除会话（软删除）"""
        conv = self.get_conversation(conversation_id)
        if conv:
            conv.is_active = False
            self.session.commit()
    
    # ==================== 消息操作 ====================
    
    def add_message(self, conversation_id: int, role: str, content: str, 
                    metadata: Optional[dict] = None, tokens_used: Optional[int] = None) -> "Message":
        """添加消息"""
        from src.database.models import Message, Conversation
        
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata,
            tokens_used=tokens_used
        )
        self.session.add(message)
        
        # 更新会话的更新时间
        conv = self.get_conversation(conversation_id)
        if conv:
            from datetime import datetime
            conv.updated_at = datetime.now()
            
            # 如果是第一条消息，自动设置标题
            if not conv.title or conv.title == "新对话":
                conv.title = content[:50] + ("..." if len(content) > 50 else "")
        
        self.session.commit()
        self.session.refresh(message)
        return message
    
    def get_conversation_messages(self, conversation_id: int, limit: Optional[int] = None) -> list:
        """获取会话的所有消息"""
        from src.database.models import Message
        
        query = (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_recent_messages(self, conversation_id: int, limit: int = 10) -> list:
        """获取最近的消息"""
        from src.database.models import Message
        
        return (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )[::-1]  # 反转为时间正序
    
    # ==================== 搜索历史 ====================
    
    def add_search_history(self, user_id: int, query: str, result_count: int = 0,
                           search_type: str = "rag", response_time: int = 0):
        """添加搜索历史"""
        from src.database.models import SearchHistory
        
        history = SearchHistory(
            user_id=user_id,
            query=query,
            result_count=result_count,
            search_type=search_type,
            response_time=response_time
        )
        self.session.add(history)
        self.session.commit()
    
    def get_user_search_history(self, user_id: int, limit: int = 50) -> list:
        """获取用户搜索历史"""
        from src.database.models import SearchHistory
        
        return (
            self.session.query(SearchHistory)
            .filter(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )
