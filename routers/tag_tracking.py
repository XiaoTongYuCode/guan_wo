"""
标签追踪路由
提供标签追踪相关的统计和可视化数据API接口
"""
# 标准库导包
import logging
from datetime import date, timedelta
from typing import Optional

# 第三方库导包
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from models import (
    UserInfo,
    TrackingOverviewResponse,
    TagTrackingResponse,
    HeatmapDataResponse,
    TagBubbleDataResponse,
    EmotionDistributionResponse,
    EmotionTrendPointResponse,
    EntryListResponse,
    EntryResponse
)
from storage.database import get_session
from routers.services.tag_tracking_service import TagTrackingService
from routers.services.journal_service import JournalService
from utils import get_current_user_or_mock

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/tracking",
    tags=["标签追踪"]
)


def _get_week_range(range_type: str) -> tuple[date, date]:
    """
    获取周或月的日期范围
    
    Args:
        range_type: 范围类型（week/month）
        
    Returns:
        (开始日期, 结束日期)元组
    """
    today = date.today()
    
    if range_type == "week":
        # 本周一
        days_since_monday = today.weekday()
        start_date = today - timedelta(days=days_since_monday)
        end_date = start_date + timedelta(days=6)
    else:  # month
        # 本月第一天和最后一天
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    return start_date, end_date


@router.get("/overview", response_model=TrackingOverviewResponse, summary="获取追踪概览")
async def get_tracking_overview(
    range_type: str = Query("week", description="范围类型：week/month"),
    is_paid: bool = Query(False, description="是否付费用户"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取全部Tab下的图表数据（热力图、标签气泡图）
    
    对应PRD 6.1.2 和 6.2.1
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        start_date, end_date = _get_week_range(range_type)
        
        tracking_service = TagTrackingService(session)
        data_health = await tracking_service.has_minimum_data(user_id, start_date, end_date)
        
        # 获取热力图数据
        heatmap_data = []
        bubble_data = []
        if data_health["has_enough"]:
            heatmap_data = await tracking_service.get_activity_heatmap(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 获取标签气泡图数据
            bubble_data = await tracking_service.get_tag_bubble_chart(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                allow_all_tags=is_paid
            )
        
        return TrackingOverviewResponse(
            success=True,
            message="获取成功",
            data={
                "heatmap": heatmap_data,
                "bubble_chart": bubble_data,
                "range_type": range_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "has_enough_data": data_health["has_enough"],
                "entry_count": data_health["entry_count"],
                "active_days": data_health["active_days"],
                "is_paid": is_paid
            }
        )
        
    except Exception as e:
        logger.error(f"获取追踪概览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取追踪概览失败: {str(e)}")


@router.get("/tag/{tag_id}", response_model=TagTrackingResponse, summary="获取标签追踪数据")
async def get_tag_tracking(
    tag_id: str,
    range_type: str = Query("week", description="范围类型：week/month"),
    is_paid: bool = Query(False, description="是否付费用户"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取指定标签的追踪数据（情绪分布、情绪曲线）
    
    对应PRD 6.2.2
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        start_date, end_date = _get_week_range(range_type)
        
        tracking_service = TagTrackingService(session)
        data_health = await tracking_service.has_minimum_data(user_id, start_date, end_date)
        if not data_health["has_enough"]:
            return TagTrackingResponse(
                success=True,
                message="数据不足，返回空数据",
                data={
                    "emotion_distribution": {
                        "positive": 0,
                        "neutral": 0,
                        "negative": 0,
                        "total": 0,
                        "positive_percent": 0.0,
                        "neutral_percent": 0.0,
                        "negative_percent": 0.0
                    },
                    "emotion_curve": [],
                    "range_type": range_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "has_enough_data": False,
                    "entry_count": data_health["entry_count"],
                    "active_days": data_health["active_days"],
                    "is_paid": is_paid
                }
            )
        
        # 获取情绪分布
        emotion_dist = await tracking_service.get_emotion_distribution_by_tag(
            user_id=user_id,
            tag_id=tag_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 获取情绪曲线
        emotion_curve = await tracking_service.get_emotion_trend_curve(
            user_id=user_id,
            tag_id=tag_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return TagTrackingResponse(
            success=True,
            message="获取成功",
            data={
                "emotion_distribution": emotion_dist,
                "emotion_curve": emotion_curve,
                "range_type": range_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "has_enough_data": True,
                "entry_count": data_health["entry_count"],
                "active_days": data_health["active_days"],
                "is_paid": is_paid
            }
        )
        
    except Exception as e:
        logger.error(f"获取标签追踪数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签追踪数据失败: {str(e)}")


@router.get("/tag/{tag_id}/entries", response_model=EntryListResponse, summary="获取标签下的条目列表")
async def get_tag_entries(
    tag_id: str,
    emotion: str = Query(..., description="情绪类型：positive/neutral/negative"),
    range_type: str = Query("week", description="范围类型：week/month"),
    limit: Optional[int] = Query(20, description="限制返回数量"),
    offset: Optional[int] = Query(0, description="偏移量"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取指定标签和情绪下的条目列表（下钻功能）
    
    对应PRD 6.2.2 的下钻交互
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        start_date, end_date = _get_week_range(range_type)
        
        tracking_service = TagTrackingService(session)
        journal_service = JournalService(session)
        data_health = await tracking_service.has_minimum_data(user_id, start_date, end_date)
        if not data_health["has_enough"]:
            return EntryListResponse(
                success=True,
                message="数据不足，返回空列表",
                data=[],
                total=0
            )
        
        entries = await tracking_service.get_entries_by_tag_and_emotion(
            user_id=user_id,
            tag_id=tag_id,
            emotion=emotion,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # 加载关联数据
        for entry in entries:
            await journal_service._load_entry_relations(entry)
        
        # 转换为响应格式
        from routers.journal import _entry_to_response
        entry_responses = [_entry_to_response(entry) for entry in entries]
        
        return EntryListResponse(
            success=True,
            message="获取成功",
            data=entry_responses,
            total=len(entry_responses)
        )
        
    except Exception as e:
        logger.error(f"获取标签条目列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签条目列表失败: {str(e)}")

