"""
闪光时刻路由
提供闪光时刻（积极事件）的查询API接口
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
    FlashMomentListResponse,
    FlashMomentDetailResponse,
    FlashMomentResponse,
    EntryImageResponse
)
from routers.services.flash_moment_service import FlashMomentService
from routers.services.journal_service import JournalService
from storage.database import get_session
from utils.auth import get_current_user_or_mock

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/flash",
    tags=["闪光时刻"]
)


def _entry_to_flash_moment_response(entry) -> FlashMomentResponse:
    """
    将Entry模型转换为FlashMomentResponse
    
    Args:
        entry: Entry模型实例
        
    Returns:
        FlashMomentResponse对象
    """
    # 生成内容摘要（前50字）
    content_summary = entry.content[:50] + "..." if len(entry.content) > 50 else entry.content
    
    # 转换图片
    images = []
    if hasattr(entry, 'images') and entry.images:
        for img in entry.images:
            images.append(EntryImageResponse(
                id=img.id,
                image_url=img.image_url,
                thumbnail_url=img.thumbnail_url,
                upload_status=img.upload_status,
                is_live_photo=img.is_live_photo,
                sort_order=img.sort_order
            ))
    
    return FlashMomentResponse(
        id=entry.id,
        user_id=entry.user_id,
        content=entry.content,
        content_summary=content_summary,
        emotion=entry.emotion or "positive",
        share_count=getattr(entry, "share_count", 0),
        images=images,
        created_at=entry.created_at
    )


@router.get("/moments", response_model=FlashMomentListResponse, summary="获取闪光时刻列表")
async def get_flash_moments(
    limit: Optional[int] = Query(20, description="限制返回数量"),
    offset: Optional[int] = Query(0, description="偏移量"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取闪光时刻列表（积极情绪的条目）
    
    对应PRD 7.1.1 的内容聚合与展示
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        flash_service = FlashMomentService(session)
        entries = await flash_service.get_flash_moments(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # 转换为响应格式
        moment_responses = [_entry_to_flash_moment_response(entry) for entry in entries]
        
        return FlashMomentListResponse(
            success=True,
            message="获取成功",
            data=moment_responses,
            total=len(moment_responses)
        )
        
    except Exception as e:
        logger.error(f"获取闪光时刻列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取闪光时刻列表失败: {str(e)}")


@router.get("/moments/{entry_id}", response_model=FlashMomentDetailResponse, summary="获取闪光时刻详情")
async def get_flash_moment_detail(
    entry_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取闪光时刻详情
    
    对应PRD 7.1.2 的卡片交互功能
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        flash_service = FlashMomentService(session)
        entry = await flash_service.get_flash_moment_detail(entry_id, user_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="闪光时刻不存在或无权限")
        
        # 加载关联数据
        journal_service = JournalService(session)
        await journal_service._load_entry_relations(entry)
        
        # 转换为响应格式
        from routers.journal import _entry_to_response
        entry_response = _entry_to_response(entry)
        
        return FlashMomentDetailResponse(
            success=True,
            message="获取成功",
            data=entry_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取闪光时刻详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取闪光时刻详情失败: {str(e)}")


@router.post("/moments/{entry_id}/share", response_model=FlashMomentDetailResponse, summary="闪光时刻分享计数")
async def share_flash_moment(
    entry_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    分享闪光时刻，计数+1
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        flash_service = FlashMomentService(session)
        entry = await flash_service.increment_share(entry_id, user_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="闪光时刻不存在或无权限")
        
        # 加载关联数据
        journal_service = JournalService(session)
        await journal_service._load_entry_relations(entry)
        
        # 转换为响应格式
        from routers.journal import _entry_to_response
        entry_response = _entry_to_response(entry)
        
        return FlashMomentDetailResponse(
            success=True,
            message="分享计数+1",
            data=entry_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"闪光时刻分享计数失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"闪光时刻分享计数失败: {str(e)}")

