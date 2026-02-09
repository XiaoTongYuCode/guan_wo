"""
闪光时刻服务类
处理闪光时刻（积极事件）的查询和展示
"""
# 标准库导包
import logging
from typing import Optional, List

# 第三方库导包
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.entry import Entry
from storage.repositories.entry_repository import EntryRepository
from storage.repositories.entry_image_repository import EntryImageRepository

# 配置日志
logger = logging.getLogger(__name__)


class FlashMomentService:
    """闪光时刻服务类"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化闪光时刻服务
        
        Args:
            session: 数据库会话
        """
        self.session = session
        self.entry_repo = EntryRepository(session)
        self.image_repo = EntryImageRepository(session)
    
    async def get_flash_moments(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        获取闪光时刻列表（积极情绪的条目）
        
        对应PRD 7.1.1 的内容聚合与展示
        
        Args:
            user_id: 用户ID
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            条目列表（按时间倒序）
        """
        # 获取所有积极情绪的条目
        entries = await self.entry_repo.get_by_emotion(
            user_id=user_id,
            emotion="positive",
            limit=limit,
            offset=offset
        )
        entries = [
            e for e in entries
            if getattr(e, "status", "success") == "success" and getattr(e, "is_visible", True)
        ]
        
        # 加载图片信息
        for entry in entries:
            images = await self.image_repo.get_by_entry_id(entry.id)
            entry.images = images
        
        return entries
    
    async def get_flash_moment_detail(
        self,
        entry_id: str,
        user_id: str
    ) -> Optional[Entry]:
        """
        获取闪光时刻详情
        
        对应PRD 7.1.2 的卡片交互功能
        
        Args:
            entry_id: 条目ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            Entry实例或None
        """
        entry = await self.entry_repo.get_by_id(entry_id)
        
        if not entry:
            return None
        
        # 验证权限和情绪
        if entry.user_id != user_id:
            return None
        
        if entry.emotion != "positive":
            return None
        if entry.status != "success" or not entry.is_visible:
            return None
        
        # 加载图片信息
        images = await self.image_repo.get_by_entry_id(entry.id)
        entry.images = images
        
        return entry
    
    async def increment_share(self, entry_id: str, user_id: str) -> Optional[Entry]:
        """
        增加闪光时刻的分享次数
        """
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry or entry.user_id != user_id:
            return None
        if entry.emotion != "positive" or entry.status != "success" or not entry.is_visible:
            return None
        new_count = (entry.share_count or 0) + 1
        return await self.entry_repo.update_by_id(entry_id, share_count=new_count)

