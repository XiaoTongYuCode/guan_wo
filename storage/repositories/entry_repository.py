"""
EntryRepository - 条目/记录Repository
"""
# 标准库导包
from datetime import datetime
from typing import Optional, List, Dict, Any

# 第三方库导包
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.entry import Entry
from storage.repositories.base import BaseRepository


class EntryRepository(BaseRepository[Entry]):
    """条目/记录Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Entry)
    
    async def get_by_user_id(
        self, 
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_desc: bool = True
    ) -> List[Entry]:
        """
        根据用户ID获取记录列表
        
        Args:
            user_id: 用户ID
            limit: 限制返回数量
            offset: 偏移量
            order_desc: 是否降序排列（按创建时间）
            
        Returns:
            记录列表
        """
        return await self.query_by_filters(
            filters={"user_id": user_id},
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_desc=order_desc
        )
    
    async def get_by_date_range(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        emotion: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        根据时间范围获取记录
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            emotion: 情绪过滤（可选）
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            记录列表
        """
        filters: Dict[str, Any] = {
            "user_id": user_id,
            "created_at": {"gte": start_time, "lte": end_time}
        }
        
        if emotion:
            filters["emotion"] = emotion
        
        return await self.query_by_filters(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_desc=True
        )
    
    async def get_by_emotion(
        self,
        user_id: str,
        emotion: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        根据情绪获取记录
        
        Args:
            user_id: 用户ID
            emotion: 情绪类型（positive/neutral/negative）
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            记录列表
        """
        return await self.query_by_filters(
            filters={"user_id": user_id, "emotion": emotion},
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_desc=True
        )
    
    async def get_by_status(
        self,
        user_id: str,
        status: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        根据状态获取记录
        
        Args:
            user_id: 用户ID
            status: 状态（sending/success/failed/violated）
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            记录列表
        """
        return await self.query_by_filters(
            filters={"user_id": user_id, "status": status},
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_desc=True
        )
    
    async def count_by_user_and_date_range(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        emotion: Optional[str] = None
    ) -> int:
        """
        统计指定用户和时间范围内的记录数
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            emotion: 情绪过滤（可选）
            
        Returns:
            记录数量
        """
        conditions = [
            Entry.user_id == user_id,
            Entry.created_at >= start_time,
            Entry.created_at <= end_time
        ]
        
        if emotion:
            conditions.append(Entry.emotion == emotion)
        
        query = select(func.count(Entry.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_word_count_stats(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        获取用户在指定时间范围内的字数统计
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计结果字典（总字数、平均字数等）
        """
        query = select(
            func.count(Entry.id),
            func.sum(Entry.word_count),
            func.avg(Entry.word_count)
        ).where(
            and_(
                Entry.user_id == user_id,
                Entry.created_at >= start_time,
                Entry.created_at <= end_time,
                Entry.word_count.isnot(None)
            )
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if row:
            count, total, avg = row
            return {
                "count": count or 0,
                "total_words": int(total or 0),
                "average_words": float(avg or 0)
            }
        
        return {"count": 0, "total_words": 0, "average_words": 0.0}

