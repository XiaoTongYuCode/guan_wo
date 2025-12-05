"""
洞察路由
提供AI洞察卡片的查询、生成等API接口
"""
# 标准库导包
import logging
from typing import Optional

# 第三方库导包
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from models import (
    UserInfo,
    InsightCardListResponse,
    InsightCardDetailResponse,
    InsightCardResponse
)
from storage.database import get_session
from routers.services.insight_service import InsightService
from utils import get_current_user_or_mock

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/insights",
    tags=["AI洞察"]
)


def _card_to_response(card) -> InsightCardResponse:
    """
    将InsightCard模型转换为InsightCardResponse
    
    Args:
        card: InsightCard模型实例
        
    Returns:
        InsightCardResponse对象
    """
    return InsightCardResponse(
        id=card.id,
        user_id=card.user_id,
        card_type=card.card_type,
        content=card.content_json,
        data_start_time=card.data_start_time,
        data_end_time=card.data_end_time,
        is_viewed=card.is_viewed,
        is_hidden=card.is_hidden,
        generated_at=card.generated_at,
        created_at=card.created_at,
        updated_at=card.updated_at
    )


@router.get("/cards", response_model=InsightCardListResponse, summary="获取洞察卡片列表")
async def get_insight_cards(
    card_type: Optional[str] = Query(None, description="卡片类型过滤"),
    is_hidden: Optional[bool] = Query(False, description="是否包含隐藏的卡片"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取当前用户的洞察卡片列表
    
    对应PRD 5.1.1 的洞察卡片主界面
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        insight_service = InsightService(session)
        cards = await insight_service.get_user_cards(
            user_id=user_id,
            is_hidden=is_hidden,
            card_type=card_type
        )
        
        # 转换为响应格式
        card_responses = [_card_to_response(card) for card in cards]
        
        return InsightCardListResponse(
            success=True,
            message="获取成功",
            data=card_responses,
            total=len(card_responses)
        )
        
    except Exception as e:
        logger.error(f"获取洞察卡片列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取洞察卡片列表失败: {str(e)}")


@router.get("/cards/{card_id}", response_model=InsightCardDetailResponse, summary="获取卡片详情")
async def get_insight_card_detail(
    card_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取单张洞察卡片详情
    
    对应PRD 5.1.3 的卡片展开功能
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        insight_service = InsightService(session)
        card = await insight_service.get_card_detail(card_id, user_id)
        
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在或无权限")
        
        # 标记为已查看
        from storage.repositories.insight_card_repository import InsightCardRepository
        card_repo = InsightCardRepository(session)
        await card_repo.mark_as_viewed(card_id)
        
        # 转换为响应格式
        card_response = _card_to_response(card)
        
        return InsightCardDetailResponse(
            success=True,
            message="获取成功",
            data=card_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取卡片详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取卡片详情失败: {str(e)}")


@router.post("/cards/generate/daily", summary="生成每日寄语")
async def generate_daily_affirmation(
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    手动触发生成每日寄语
    
    对应PRD 5.1.2 卡片一：每日寄语
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        insight_service = InsightService(session)
        card = await insight_service.generate_daily_affirmation(user_id)
        
        if not card:
            raise HTTPException(status_code=500, detail="生成每日寄语失败")
        
        card_response = _card_to_response(card)
        
        return InsightCardDetailResponse(
            success=True,
            message="生成成功",
            data=card_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成每日寄语失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成每日寄语失败: {str(e)}")


@router.post("/cards/generate/weekly-emotion", summary="生成每周情绪地图")
async def generate_weekly_emotion_map(
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    手动触发生成每周情绪地图
    
    对应PRD 5.1.2 卡片二：每周情绪地图
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        insight_service = InsightService(session)
        card = await insight_service.generate_weekly_emotion_map(user_id)
        
        if not card:
            raise HTTPException(status_code=400, detail="数据不足，无法生成情绪地图（需要至少3条记录）")
        
        card_response = _card_to_response(card)
        
        return InsightCardDetailResponse(
            success=True,
            message="生成成功",
            data=card_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成每周情绪地图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成每周情绪地图失败: {str(e)}")


@router.post("/cards/generate/weekly-gratitude", summary="生成每周感恩清单")
async def generate_weekly_gratitude_list(
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    手动触发生成每周感恩清单
    
    对应PRD 5.1.2 卡片三：每周感恩清单
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        insight_service = InsightService(session)
        card = await insight_service.generate_weekly_gratitude_list(user_id)
        
        if not card:
            raise HTTPException(status_code=400, detail="数据不足，无法生成感恩清单（需要至少1条积极事件）")
        
        card_response = _card_to_response(card)
        
        return InsightCardDetailResponse(
            success=True,
            message="生成成功",
            data=card_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成每周感恩清单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成每周感恩清单失败: {str(e)}")

