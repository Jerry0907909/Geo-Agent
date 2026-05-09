"""数据库模块

提供数据库连接、模型定义和管理功能。
"""

from src.database.models import (
    Base,
    User,
    Conversation,
    Message,
    UserPreference,
    SearchHistory,
    DocumentAccess,
)
from src.database.mysql_manager import (
    get_db,
    get_db_session,
    init_database,
    check_database_connection,
    close_database,
    MySQLManager,
)
from src.database.chroma_manager import (
    ChromaManager,
    create_chroma_manager,
    list_all_collections,
)

__all__ = [
    # Models
    "Base",
    "User",
    "Conversation",
    "Message",
    "UserPreference",
    "SearchHistory",
    "DocumentAccess",
    # MySQL
    "get_db",
    "get_db_session",
    "init_database",
    "check_database_connection",
    "close_database",
    "MySQLManager",
    # Chroma
    "ChromaManager",
    "create_chroma_manager",
    "list_all_collections",
]
