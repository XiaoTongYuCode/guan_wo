"""
Storage层包
提供数据库连接、模型和Repository的统一访问接口
"""
# 项目内部导包
from .database import (
    get_session,
    init_db,
    cleanup_db,
    Base,
    engine,
    async_session_factory
)
from .models import (
    Entry,
    EntryImage,
    Tag,
    EntryTag,
    InsightCard,
    InsightCardConfig
)
from .repositories import (
    BaseRepository,
    EntryRepository,
    EntryImageRepository,
    TagRepository,
    EntryTagRepository,
    InsightCardRepository,
    InsightCardConfigRepository
)

__all__ = [
    # 数据库连接相关
    "get_session",
    "init_db", 
    "cleanup_db",
    "Base",
    "engine",
    "async_session_factory",
    
    # 模型相关
    "Entry",
    "EntryImage",
    "Tag",
    "EntryTag",
    "InsightCard",
    "InsightCardConfig",
    
    # Repository相关
    "BaseRepository",
    "EntryRepository",
    "EntryImageRepository",
    "TagRepository",
    "EntryTagRepository",
    "InsightCardRepository",
    "InsightCardConfigRepository",
]
