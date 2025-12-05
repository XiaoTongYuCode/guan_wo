"""
InsightCardRepository - 洞察卡片Repository
"""
# 标准库导包
from datetime import datetime
from typing import Optional, List, Dict, Any

# 第三方库导包
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.insight_card import InsightCard
from storage.repositories.base import BaseRepository


class InsightCardRepository(BaseRepository[InsightCard]):
    """洞察卡片Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, InsightCard)
    
    async def get_by_user_id(
        self,
        user_id: str,
        is_hidden: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[InsightCard]:
        """
        根据用户ID获取洞察卡片
        
        Args:
            user_id: 用户ID
            is_hidden: 是否隐藏（可选）
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            洞察卡片列表
        """
        filters: Dict[str, Any] = {"user_id": user_id}
        
        if is_hidden is not None:
            filters["is_hidden"] = is_hidden
        
        return await self.query_by_filters(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="generated_at",
            order_desc=True
        )
    
    async def get_by_card_type(
        self,
        user_id: str,
        card_type: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[InsightCard]:
        """
        根据卡片类型获取洞察卡片
        
        Args:
            user_id: 用户ID
            card_type: 卡片类型
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            洞察卡片列表
        """
        return await self.query_by_filters(
            filters={"user_id": user_id, "card_type": card_type},
            limit=limit,
            offset=offset,
            order_by="generated_at",
            order_desc=True
        )
    
    async def get_by_date_range(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        card_type: Optional[str] = None
    ) -> List[InsightCard]:
        """
        根据生成时间范围获取洞察卡片
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            card_type: 卡片类型（可选）
            
        Returns:
            洞察卡片列表
        """
        filters: Dict[str, Any] = {
            "user_id": user_id,
            "generated_at": {"gte": start_time, "lte": end_time}
        }
        
        if card_type:
            filters["card_type"] = card_type
        
        return await self.query_by_filters(
            filters=filters,
            order_by="generated_at",
            order_desc=True
        )
    
    async def get_by_config_id(
        self,
        config_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[InsightCard]:
        """
        根据配置ID获取洞察卡片
        
        Args:
            config_id: 配置ID
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            洞察卡片列表
        """
        return await self.query_by_filters(
            filters={"config_id": config_id},
            limit=limit,
            offset=offset,
            order_by="generated_at",
            order_desc=True
        )
    
    async def get_latest_by_type(
        self,
        user_id: str,
        card_type: str
    ) -> Optional[InsightCard]:
        """
        获取指定类型的最新洞察卡片
        
        Args:
            user_id: 用户ID
            card_type: 卡片类型
            
        Returns:
            最新的洞察卡片或None
        """
        results = await self.query_by_filters(
            filters={"user_id": user_id, "card_type": card_type, "is_hidden": False},
            limit=1,
            order_by="generated_at",
            order_desc=True
        )
        return results[0] if results else None
    
    async def mark_as_viewed(self, card_id: str) -> Optional[InsightCard]:
        """
        标记卡片为已查看
        
        Args:
            card_id: 卡片ID
            
        Returns:
            更新后的卡片实例
        """
        card = await self.get_by_id(card_id)
        if card:
            return await self.update_by_id(card_id, is_viewed=True, view_count=card.view_count + 1)
        return None
    
    async def mark_as_hidden(self, card_id: str) -> Optional[InsightCard]:
        """
        标记卡片为已隐藏
        
        Args:
            card_id: 卡片ID
            
        Returns:
            更新后的卡片实例
        """
        return await self.update_by_id(card_id, is_hidden=True)
    
    async def increment_share_count(self, card_id: str) -> Optional[InsightCard]:
        """
        增加分享次数
        
        Args:
            card_id: 卡片ID
            
        Returns:
            更新后的卡片实例
        """
        card = await self.get_by_id(card_id)
        if card:
            return await self.update_by_id(card_id, share_count=card.share_count + 1)
        return None
    
    async def check_card_exists(
        self,
        user_id: str,
        card_type: str,
        data_start_time: datetime,
        data_end_time: datetime
    ) -> bool:
        """
        检查指定条件的卡片是否已存在
        
        Args:
            user_id: 用户ID
            card_type: 卡片类型
            data_start_time: 数据开始时间
            data_end_time: 数据结束时间
            
        Returns:
            是否存在
        """
        query = select(InsightCard).where(
            and_(
                InsightCard.user_id == user_id,
                InsightCard.card_type == card_type,
                InsightCard.data_start_time == data_start_time,
                InsightCard.data_end_time == data_end_time
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

