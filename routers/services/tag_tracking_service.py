"""
标签追踪服务类
处理标签追踪相关的统计和可视化数据
"""
# 标准库导包
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

# 第三方库导包
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

# 项目内部导包
from storage.models.entry import Entry
from storage.models.entry_tag import EntryTag
from storage.models.tag import Tag
from storage.repositories.entry_repository import EntryRepository
from storage.repositories.entry_tag_repository import EntryTagRepository
from storage.repositories.tag_repository import TagRepository

# 配置日志
logger = logging.getLogger(__name__)


class TagTrackingService:
    """标签追踪服务类"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化标签追踪服务
        
        Args:
            session: 数据库会话
        """
        self.session = session
        self.entry_repo = EntryRepository(session)
        self.tag_repo = TagRepository(session)
        self.entry_tag_repo = EntryTagRepository(session)
    
    async def get_activity_heatmap(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取记录热力图数据
        
        对应PRD 6.2.1 图表一：记录热力图
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            热力图数据列表，每个元素包含 date 和 count
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 获取时间范围内的所有记录
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # 按日期统计
        daily_counts = {}
        for entry in entries:
            day = entry.created_at.date()
            if day not in daily_counts:
                daily_counts[day] = {"count": 0, "word_count": 0}
            daily_counts[day]["count"] += 1
            daily_counts[day]["word_count"] += entry.word_count or 0
        
        # 转换为列表格式
        heatmap_data = []
        current_date = start_date
        while current_date <= end_date:
            day_data = daily_counts.get(current_date, {"count": 0, "word_count": 0})
            heatmap_data.append({
                "date": current_date.isoformat(),
                "count": day_data["count"],
                "word_count": day_data["word_count"]
            })
            current_date += timedelta(days=1)
        
        return heatmap_data
    
    async def get_tag_bubble_chart(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取标签气泡图数据
        
        对应PRD 6.2.1 图表二：标签气泡图
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            标签气泡图数据列表
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 获取时间范围内的所有记录ID
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        entry_ids = [entry.id for entry in entries]
        
        if not entry_ids:
            return []
        
        # 统计每个标签关联的事件数
        query = select(
            Tag.id,
            Tag.name,
            Tag.color,
            func.count(EntryTag.id).label("event_count")
        ).join(
            EntryTag, Tag.id == EntryTag.tag_id
        ).where(
            EntryTag.entry_id.in_(entry_ids)
        ).group_by(
            Tag.id, Tag.name, Tag.color
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        bubble_data = []
        for row in rows:
            bubble_data.append({
                "tag_id": row.id,
                "tag_name": row.name,
                "color": row.color,
                "event_count": row.event_count
            })
        
        return bubble_data
    
    async def get_emotion_distribution_by_tag(
        self,
        user_id: str,
        tag_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        获取指定标签下的情绪分布
        
        对应PRD 6.2.2 图表一：情绪占比横条图
        
        Args:
            user_id: 用户ID
            tag_id: 标签ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            情绪分布数据
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 获取该标签下的所有条目ID
        entry_ids = await self.entry_tag_repo.get_entry_ids_by_tag_id(tag_id)
        
        if not entry_ids:
            return {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "total": 0,
                "positive_percent": 0.0,
                "neutral_percent": 0.0,
                "negative_percent": 0.0
            }
        
        # 获取这些条目并过滤时间和用户
        query = select(Entry).where(
            and_(
                Entry.id.in_(entry_ids),
                Entry.user_id == user_id,
                Entry.created_at >= start_time,
                Entry.created_at <= end_time
            )
        )
        
        result = await self.session.execute(query)
        entries = list(result.scalars().all())
        
        # 统计情绪分布
        emotion_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for entry in entries:
            if entry.emotion:
                emotion_counts[entry.emotion] = emotion_counts.get(entry.emotion, 0) + 1
        
        total = len(entries)
        
        return {
            "positive": emotion_counts.get("positive", 0),
            "neutral": emotion_counts.get("neutral", 0),
            "negative": emotion_counts.get("negative", 0),
            "total": total,
            "positive_percent": (emotion_counts.get("positive", 0) / total * 100) if total > 0 else 0.0,
            "neutral_percent": (emotion_counts.get("neutral", 0) / total * 100) if total > 0 else 0.0,
            "negative_percent": (emotion_counts.get("negative", 0) / total * 100) if total > 0 else 0.0
        }
    
    async def get_emotion_trend_curve(
        self,
        user_id: str,
        tag_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取情绪变化曲线数据
        
        对应PRD 6.2.2 图表二：情绪变化曲线图
        
        Args:
            user_id: 用户ID
            tag_id: 标签ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            情绪曲线数据列表
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 获取该标签下的所有条目ID
        entry_ids = await self.entry_tag_repo.get_entry_ids_by_tag_id(tag_id)
        
        if not entry_ids:
            return []
        
        # 获取这些条目并过滤时间和用户
        query = select(Entry).where(
            and_(
                Entry.id.in_(entry_ids),
                Entry.user_id == user_id,
                Entry.created_at >= start_time,
                Entry.created_at <= end_time
            )
        )
        
        result = await self.session.execute(query)
        entries = list(result.scalars().all())
        
        # 按日期分组统计
        daily_stats = {}
        for entry in entries:
            day = entry.created_at.date()
            if day not in daily_stats:
                daily_stats[day] = {"positive": 0, "total": 0}
            daily_stats[day]["total"] += 1
            if entry.emotion == "positive":
                daily_stats[day]["positive"] += 1
        
        # 计算每日情绪得分
        curve_data = []
        current_date = start_date
        while current_date <= end_date:
            day_stats = daily_stats.get(current_date, {"positive": 0, "total": 0})
            
            if day_stats["total"] > 0:
                score = day_stats["positive"] / day_stats["total"]
            else:
                score = 0.0
            
            curve_data.append({
                "date": current_date.isoformat(),
                "score": score,
                "positive_count": day_stats["positive"],
                "total_count": day_stats["total"]
            })
            
            current_date += timedelta(days=1)
        
        return curve_data
    
    async def get_entries_by_tag_and_emotion(
        self,
        user_id: str,
        tag_id: str,
        emotion: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        获取指定标签和情绪下的条目列表（用于下钻）
        
        对应PRD 6.2.2 的下钻功能
        
        Args:
            user_id: 用户ID
            tag_id: 标签ID
            emotion: 情绪类型（positive/neutral/negative）
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            条目列表
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # 获取该标签下的所有条目ID
        entry_ids = await self.entry_tag_repo.get_entry_ids_by_tag_id(tag_id)
        
        if not entry_ids:
            return []
        
        # 获取这些条目并过滤时间、用户和情绪
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            emotion=emotion
        )
        
        # 过滤出属于该标签的条目
        filtered_entries = [e for e in entries if e.id in entry_ids]
        
        # 应用分页
        if offset:
            filtered_entries = filtered_entries[offset:]
        if limit:
            filtered_entries = filtered_entries[:limit]
        
        return filtered_entries

