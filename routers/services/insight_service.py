"""
洞察服务类
处理AI洞察卡片的生成、查询等业务逻辑
"""
# 标准库导包
import logging
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

# 第三方库导包
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.insight_card import InsightCard
from storage.models.insight_card_config import InsightCardConfig
from storage.repositories.entry_repository import EntryRepository
from storage.repositories.insight_card_repository import InsightCardRepository
from storage.repositories.insight_card_config_repository import InsightCardConfigRepository
from llm.client import LLMClient
from prompt import (
    DAILY_AFFIRMATION_SYSTEM_PROMPT,
    DAILY_AFFIRMATION_USER_PROMPT_POSITIVE,
    DAILY_AFFIRMATION_USER_PROMPT_NEGATIVE,
    DAILY_AFFIRMATION_USER_PROMPT_NEUTRAL,
    EMOTION_SUMMARY_SYSTEM_PROMPT,
    EMOTION_SUMMARY_USER_PROMPT
)

# 配置日志
logger = logging.getLogger(__name__)


class InsightService:
    """洞察服务类"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化洞察服务
        
        Args:
            session: 数据库会话
        """
        self.session = session
        self.entry_repo = EntryRepository(session)
        self.card_repo = InsightCardRepository(session)
        self.config_repo = InsightCardConfigRepository(session)
        self.llm_client = LLMClient()
    
    async def generate_daily_affirmation(
        self,
        user_id: str,
        target_date: Optional[date] = None
    ) -> Optional[InsightCard]:
        """
        生成每日寄语
        
        对应PRD 5.1.2 卡片一：每日寄语
        
        Args:
            user_id: 用户ID
            target_date: 目标日期，如果为None则使用昨天
            
        Returns:
            InsightCard实例或None
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        # 检查是否已生成
        data_start = datetime.combine(target_date, datetime.min.time())
        data_end = datetime.combine(target_date, datetime.max.time())
        
        existing = await self.card_repo.check_card_exists(
            user_id=user_id,
            card_type="daily_affirmation",
            data_start_time=data_start,
            data_end_time=data_end
        )
        
        if existing:
            return await self.card_repo.get_latest_by_type(user_id, "daily_affirmation")
        
        # 获取前一日记录
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=data_start,
            end_time=data_end
        )
        
        # 分析情绪
        emotion_summary = self._analyze_emotion_summary(entries)
        
        # 生成寄语
        if entries:
            # 有记录：根据情绪生成寄语
            affirmation = await self._generate_affirmation_by_emotion(emotion_summary, entries)
        else:
            # 无记录：从预设库随机选择
            affirmation = self._get_default_affirmation()
        
        # 创建卡片
        card = await self.card_repo.create(
            user_id=user_id,
            card_type="daily_affirmation",
            content_json={"affirmation": affirmation},
            data_start_time=data_start,
            data_end_time=data_end,
            is_viewed=False,
            is_hidden=False
        )
        
        logger.info(f"生成每日寄语成功: card_id={card.id}, user_id={user_id}")
        return card
    
    async def generate_weekly_emotion_map(
        self,
        user_id: str,
        week_start: Optional[date] = None
    ) -> Optional[InsightCard]:
        """
        生成每周情绪地图
        
        对应PRD 5.1.2 卡片二：每周情绪地图
        
        Args:
            user_id: 用户ID
            week_start: 周开始日期（周一），如果为None则使用上周一
            
        Returns:
            InsightCard实例或None
        """
        if week_start is None:
            # 计算上周一
            today = date.today()
            days_since_monday = (today.weekday()) % 7
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday
        
        week_end = week_start + timedelta(days=6)
        data_start = datetime.combine(week_start, datetime.min.time())
        data_end = datetime.combine(week_end, datetime.max.time())
        
        # 检查是否已生成
        existing = await self.card_repo.check_card_exists(
            user_id=user_id,
            card_type="weekly_emotion_map",
            data_start_time=data_start,
            data_end_time=data_end
        )
        
        if existing:
            return await self.card_repo.get_latest_by_type(user_id, "weekly_emotion_map")
        
        # 获取周记录
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=data_start,
            end_time=data_end
        )
        
        # 数据不足检查
        if len(entries) < 3:
            logger.info(f"周记录不足，无法生成情绪地图: user_id={user_id}, count={len(entries)}")
            return None
        
        # 统计情绪分布
        emotion_stats = self._calculate_emotion_stats(entries)
        
        # 计算每日情绪得分
        daily_scores = self._calculate_daily_emotion_scores(entries, week_start)
        
        # 生成摘要
        summary = await self._generate_emotion_summary(emotion_stats, daily_scores, week_start)
        
        # 创建卡片
        card = await self.card_repo.create(
            user_id=user_id,
            card_type="weekly_emotion_map",
            content_json={
                "emotion_stats": emotion_stats,
                "daily_scores": daily_scores,
                "summary": summary
            },
            data_start_time=data_start,
            data_end_time=data_end,
            is_viewed=False,
            is_hidden=False
        )
        
        logger.info(f"生成每周情绪地图成功: card_id={card.id}, user_id={user_id}")
        return card
    
    async def generate_weekly_gratitude_list(
        self,
        user_id: str,
        week_start: Optional[date] = None
    ) -> Optional[InsightCard]:
        """
        生成每周感恩清单
        
        对应PRD 5.1.2 卡片三：每周感恩清单
        
        Args:
            user_id: 用户ID
            week_start: 周开始日期（周一），如果为None则使用上周一
            
        Returns:
            InsightCard实例或None
        """
        if week_start is None:
            # 计算上周一
            today = date.today()
            days_since_monday = (today.weekday()) % 7
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday
        
        week_end = week_start + timedelta(days=6)
        data_start = datetime.combine(week_start, datetime.min.time())
        data_end = datetime.combine(week_end, datetime.max.time())
        
        # 检查是否已生成
        existing = await self.card_repo.check_card_exists(
            user_id=user_id,
            card_type="weekly_gratitude_list",
            data_start_time=data_start,
            data_end_time=data_end
        )
        
        if existing:
            return await self.card_repo.get_latest_by_type(user_id, "weekly_gratitude_list")
        
        # 获取积极情绪记录
        positive_entries = await self.entry_repo.get_by_emotion(
            user_id=user_id,
            emotion="positive",
            limit=50  # 获取足够多的记录以便筛选
        )
        
        # 过滤时间范围
        positive_entries = [
            e for e in positive_entries
            if data_start <= e.created_at <= data_end
        ]
        
        # 数据不足检查
        if len(positive_entries) < 1:
            logger.info(f"积极事件不足，无法生成感恩清单: user_id={user_id}")
            return None
        
        # 选择3-5个代表性事件
        selected_events = self._select_representative_events(positive_entries, min(5, len(positive_entries)))
        
        # 创建卡片
        card = await self.card_repo.create(
            user_id=user_id,
            card_type="weekly_gratitude_list",
            content_json={"events": selected_events},
            data_start_time=data_start,
            data_end_time=data_end,
            is_viewed=False,
            is_hidden=False
        )
        
        logger.info(f"生成每周感恩清单成功: card_id={card.id}, user_id={user_id}")
        return card
    
    def _analyze_emotion_summary(self, entries: List) -> Dict[str, int]:
        """分析情绪摘要"""
        stats = {"positive": 0, "neutral": 0, "negative": 0}
        for entry in entries:
            if entry.emotion:
                stats[entry.emotion] = stats.get(entry.emotion, 0) + 1
        return stats
    
    async def _generate_affirmation_by_emotion(
        self,
        emotion_summary: Dict[str, int],
        entries: List
    ) -> str:
        """根据情绪生成寄语"""
        total = sum(emotion_summary.values())
        if total == 0:
            return self._get_default_affirmation()
        
        positive_ratio = emotion_summary.get("positive", 0) / total
        negative_ratio = emotion_summary.get("negative", 0) / total
        
        # 构建提示词
        system_prompt = DAILY_AFFIRMATION_SYSTEM_PROMPT
        
        # 确定情绪类型并选择对应的提示词模板
        if positive_ratio > 0.6:
            user_prompt = DAILY_AFFIRMATION_USER_PROMPT_POSITIVE
        elif negative_ratio > 0.6:
            user_prompt = DAILY_AFFIRMATION_USER_PROMPT_NEGATIVE
        else:
            user_prompt = DAILY_AFFIRMATION_USER_PROMPT_NEUTRAL
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            affirmation = await self.llm_client.chat(messages, temperature=0.8)
            return affirmation.strip()
        except Exception as e:
            logger.error(f"生成寄语失败: {str(e)}")
            return self._get_default_affirmation()
    
    def _get_default_affirmation(self) -> str:
        """获取默认寄语"""
        affirmations = [
            "今天也是新的一天，保持积极的心态，一切都会好起来的。",
            "每一个今天都是新的开始，相信自己，你可以的。",
            "生活就像一面镜子，你对它笑，它也会对你笑。",
            "保持微笑，保持希望，美好的事情正在路上。",
            "每一天都是成长的机会，加油！"
        ]
        import random
        return random.choice(affirmations)
    
    def _calculate_emotion_stats(self, entries: List) -> Dict[str, int]:
        """计算情绪统计"""
        stats = {"positive": 0, "neutral": 0, "negative": 0}
        for entry in entries:
            if entry.emotion:
                stats[entry.emotion] = stats.get(entry.emotion, 0) + 1
        return stats
    
    def _calculate_daily_emotion_scores(
        self,
        entries: List,
        week_start: date
    ) -> List[Dict[str, Any]]:
        """计算每日情绪得分"""
        daily_entries = {}
        for entry in entries:
            day = entry.created_at.date()
            if day not in daily_entries:
                daily_entries[day] = {"positive": 0, "total": 0}
            daily_entries[day]["total"] += 1
            if entry.emotion == "positive":
                daily_entries[day]["positive"] += 1
        
        scores = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_entries = daily_entries.get(day, {"positive": 0, "total": 0})
            if day_entries["total"] > 0:
                score = day_entries["positive"] / day_entries["total"]
            else:
                score = 0.0
            scores.append({
                "date": day.isoformat(),
                "score": score,
                "positive_count": day_entries["positive"],
                "total_count": day_entries["total"]
            })
        
        return scores
    
    async def _generate_emotion_summary(
        self,
        emotion_stats: Dict[str, int],
        daily_scores: List[Dict[str, Any]],
        week_start: date
    ) -> str:
        """生成情绪摘要"""
        total = sum(emotion_stats.values())
        positive_ratio = emotion_stats.get("positive", 0) / total if total > 0 else 0
        
        # 找出情绪最高和最低的一天
        max_day = max(daily_scores, key=lambda x: x["score"])
        min_day = min(daily_scores, key=lambda x: x["score"])
        
        system_prompt = EMOTION_SUMMARY_SYSTEM_PROMPT
        user_prompt = EMOTION_SUMMARY_USER_PROMPT.format(
            positive_count=emotion_stats.get('positive', 0),
            neutral_count=emotion_stats.get('neutral', 0),
            negative_count=emotion_stats.get('negative', 0),
            positive_ratio=positive_ratio,
            max_day_date=max_day['date'],
            max_day_score=max_day['score'],
            min_day_date=min_day['date'],
            min_day_score=min_day['score']
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            summary = await self.llm_client.chat(messages, temperature=0.5)
            return summary.strip()
        except Exception as e:
            logger.error(f"生成情绪摘要失败: {str(e)}")
            return f"本周整体情绪积极率为{positive_ratio:.1%}，情绪最高的一天是{max_day['date']}，最低的一天是{min_day['date']}。"
    
    def _select_representative_events(
        self,
        entries: List,
        count: int
    ) -> List[Dict[str, Any]]:
        """选择代表性事件"""
        # 简单策略：选择字数较多、较完整的记录
        sorted_entries = sorted(
            entries,
            key=lambda e: e.word_count or 0,
            reverse=True
        )
        
        selected = sorted_entries[:count]
        return [
            {
                "id": entry.id,
                "content": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content,
                "created_at": entry.created_at.isoformat()
            }
            for entry in selected
        ]
    
    async def get_user_cards(
        self,
        user_id: str,
        is_hidden: Optional[bool] = False,
        card_type: Optional[str] = None
    ) -> List[InsightCard]:
        """
        获取用户的洞察卡片列表
        
        Args:
            user_id: 用户ID
            is_hidden: 是否包含隐藏的卡片
            card_type: 卡片类型过滤（可选）
            
        Returns:
            洞察卡片列表
        """
        if card_type:
            return await self.card_repo.get_by_card_type(
                user_id=user_id,
                card_type=card_type
            )
        else:
            return await self.card_repo.get_by_user_id(
                user_id=user_id,
                is_hidden=is_hidden
            )
    
    async def get_card_detail(self, card_id: str, user_id: str) -> Optional[InsightCard]:
        """
        获取卡片详情
        
        Args:
            card_id: 卡片ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            InsightCard实例或None
        """
        card = await self.card_repo.get_by_id(card_id)
        if card and card.user_id == user_id:
            return card
        return None

