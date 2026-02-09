"""
洞察路由
提供AI洞察卡片的查询、生成等API接口
"""
# 标准库导包
import logging
from typing import Optional

# 第三方库导包
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from models import (
    UserInfo,
    InsightCardListResponse,
    InsightCardDetailResponse,
    InsightCardResponse,
    InsightCardConfigListResponse,
    InsightCardConfigResponse,
    CreateInsightCardConfigRequest,
    UpdateInsightCardConfigRequest,
    ReorderInsightConfigsRequest
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
    try:
        # 确保 content_json 是有效的字典
        content = card.content_json if card.content_json is not None else {}
        if not isinstance(content, dict):
            logger.warning(f"卡片 {card.id} 的 content_json 不是字典类型: {type(content)}")
            content = {}
        
        return InsightCardResponse(
            id=card.id,
            user_id=card.user_id,
            card_type=card.card_type,
            content=content,
            data_start_time=card.data_start_time,
            data_end_time=card.data_end_time,
            is_viewed=card.is_viewed,
            is_hidden=card.is_hidden,
            generated_at=card.generated_at,
            created_at=card.created_at,
            updated_at=card.updated_at
        )
    except Exception as e:
        logger.error(f"转换卡片响应失败: card_id={card.id}, error={str(e)}")
        raise


def _config_to_response(config) -> InsightCardConfigResponse:
    """将配置模型转换为响应"""
    return InsightCardConfigResponse(
        id=config.id,
        user_id=config.user_id,
        name=config.name,
        card_type=config.card_type,
        time_range=config.time_range,
        prompt=config.prompt,
        sort_order=config.sort_order,
        is_enabled=config.is_enabled,
        is_system=config.is_system,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/cards", response_model=InsightCardListResponse, summary="获取洞察卡片列表")
async def get_insight_cards(
    card_type: Optional[str] = Query(None, description="卡片类型过滤"),
    is_hidden: Optional[bool] = Query(False, description="是否包含隐藏的卡片（False表示只返回未隐藏的）"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取当前用户的洞察卡片列表
    
    对应PRD 5.1.1 的洞察卡片主界面
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        if not user_id:
            logger.warning("用户ID为空，使用mock用户")
            user_id = "mock_user_001"
        
        logger.info(f"获取洞察卡片列表: user_id={user_id}, is_hidden={is_hidden}, card_type={card_type}")
        
        insight_service = InsightService(session)
        cards = await insight_service.get_user_cards(
            user_id=user_id,
            is_hidden=is_hidden,
            card_type=card_type
        )
        
        logger.info(f"查询到 {len(cards)} 张卡片")
        
        # 转换为响应格式
        card_responses = []
        for card in cards:
            try:
                response = _card_to_response(card)
                card_responses.append(response)
            except Exception as e:
                logger.error(f"转换卡片失败: card_id={card.id}, error={str(e)}")
                # 跳过有问题的卡片，继续处理其他卡片
                continue
        
        return InsightCardListResponse(
            success=True,
            message="获取成功",
            data=card_responses,
            total=len(card_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取洞察卡片列表失败: {str(e)}", exc_info=True)
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


@router.post("/cards/{card_id}/hide", summary="隐藏卡片")
async def hide_insight_card(
    card_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        card = await insight_service.hide_card(card_id, user_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在或无权限")
        return {"success": True, "message": "已隐藏"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"隐藏卡片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"隐藏卡片失败: {str(e)}")


@router.post("/cards/{card_id}/show", summary="取消隐藏卡片")
async def show_insight_card(
    card_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        card = await insight_service.unhide_card(card_id, user_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在或无权限")
        card_response = _card_to_response(card)
        return InsightCardDetailResponse(
            success=True,
            message="已取消隐藏",
            data=card_response
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消隐藏卡片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消隐藏卡片失败: {str(e)}")


@router.post("/cards/{card_id}/share", summary="分享计数")
async def share_insight_card(
    card_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        card = await insight_service.increment_share(card_id, user_id)
        if not card:
            raise HTTPException(status_code=404, detail="卡片不存在或无权限")
        card_response = _card_to_response(card)
        return InsightCardDetailResponse(
            success=True,
            message="分享计数+1",
            data=card_response
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分享计数失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分享计数失败: {str(e)}")


@router.get("/configs", response_model=InsightCardConfigListResponse, summary="获取洞察配置列表")
async def list_insight_configs(
    include_hidden: bool = Query(True, description="是否包含隐藏配置"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        configs = await insight_service.list_configs(user_id)
        if not include_hidden:
            configs = [cfg for cfg in configs if cfg.is_enabled]
        config_responses = [_config_to_response(cfg) for cfg in configs]
        return InsightCardConfigListResponse(
            success=True,
            message="获取成功",
            data=config_responses,
            total=len(config_responses)
        )
    except Exception as e:
        logger.error(f"获取洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取洞察配置失败: {str(e)}")


@router.post("/configs", response_model=InsightCardConfigResponse, summary="创建自定义洞察配置")
async def create_insight_config(
    request: CreateInsightCardConfigRequest,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    x_member_tier: str = Header(default="free", alias="X-Member-Tier"),
    session: AsyncSession = Depends(get_session)
):
    try:
        is_paid_user = x_member_tier.lower() in {"paid", "pro", "vip"}
        if not is_paid_user:
            raise HTTPException(status_code=403, detail="仅付费用户可创建洞察配置")
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.create_config(
            user_id=user_id,
            name=request.name,
            time_range=request.time_range,
            prompt=request.prompt
        )
        return _config_to_response(config)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"创建洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建洞察配置失败: {str(e)}")


@router.put("/configs/{config_id}", response_model=InsightCardConfigResponse, summary="更新自定义洞察配置")
async def update_insight_config(
    config_id: str,
    request: UpdateInsightCardConfigRequest,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    x_member_tier: str = Header(default="free", alias="X-Member-Tier"),
    session: AsyncSession = Depends(get_session)
):
    try:
        is_paid_user = x_member_tier.lower() in {"paid", "pro", "vip"}
        if not is_paid_user:
            raise HTTPException(status_code=403, detail="仅付费用户可编辑洞察配置")
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.update_config(
            config_id=config_id,
            user_id=user_id,
            name=request.name,
            time_range=request.time_range,
            prompt=request.prompt
        )
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        return _config_to_response(config)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新洞察配置失败: {str(e)}")


@router.delete("/configs/{config_id}", summary="删除洞察配置")
async def delete_insight_config(
    config_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    x_member_tier: str = Header(default="free", alias="X-Member-Tier"),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.get_config(config_id, user_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        is_paid_user = x_member_tier.lower() in {"paid", "pro", "vip"}
        if not is_paid_user and not config.is_system:
            raise HTTPException(status_code=403, detail="仅付费用户可删除自定义洞察配置")
        success = await insight_service.delete_config(config_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        return {"success": True, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除洞察配置失败: {str(e)}")


@router.post("/configs/{config_id}/hide", response_model=InsightCardConfigResponse, summary="隐藏洞察配置")
async def hide_insight_config(
    config_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.set_config_enabled(config_id, user_id, False)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        return _config_to_response(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"隐藏洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"隐藏洞察配置失败: {str(e)}")


@router.post("/configs/{config_id}/show", response_model=InsightCardConfigResponse, summary="恢复洞察配置")
async def show_insight_config(
    config_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.set_config_enabled(config_id, user_id, True)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        return _config_to_response(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"恢复洞察配置失败: {str(e)}")


@router.post("/configs/reorder", response_model=InsightCardConfigListResponse, summary="洞察配置排序")
async def reorder_insight_configs(
    request: ReorderInsightConfigsRequest,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    x_member_tier: str = Header(default="free", alias="X-Member-Tier"),
    session: AsyncSession = Depends(get_session)
):
    try:
        is_paid_user = x_member_tier.lower() in {"paid", "pro", "vip"}
        if not is_paid_user:
            raise HTTPException(status_code=403, detail="仅付费用户可排序洞察配置")
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        configs = await insight_service.reorder_configs(user_id, request.config_ids)
        config_responses = [_config_to_response(cfg) for cfg in configs]
        return InsightCardConfigListResponse(
            success=True,
            message="排序成功",
            data=config_responses,
            total=len(config_responses)
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"排序洞察配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"排序洞察配置失败: {str(e)}")

@router.post("/configs/{config_id}/toggle", response_model=InsightCardConfigResponse, summary="切换洞察配置启用状态")
async def toggle_insight_config(
    config_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    try:
        user_id = user_info.user_id or user_info.mobile
        insight_service = InsightService(session)
        config = await insight_service.toggle_config(config_id, user_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在或无权限")
        return _config_to_response(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换配置状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"切换配置状态失败: {str(e)}")
