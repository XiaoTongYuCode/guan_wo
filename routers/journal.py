"""
日记路由
提供日记条目的创建、查询、重试等API接口
"""
# 标准库导包
import logging
from datetime import date
from typing import Optional

# 第三方库导包
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from models import (
    UserInfo,
    CreateEntryRequest,
    CreateEntryResponse,
    EntryListResponse,
    EntryResponse,
    RetryEntryResponse,
    TagListResponse,
    TagResponse,
    EntryImageResponse
)
from storage.database import get_session
from routers.services.journal_service import JournalService
from utils import get_current_user_or_mock

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/journal",
    tags=["日记记录"]
)


def _entry_to_response(entry) -> EntryResponse:
    """
    将Entry模型转换为EntryResponse
    
    Args:
        entry: Entry模型实例
        
    Returns:
        EntryResponse对象
    """
    # 提取事件列表
    events = []
    if entry.events_json and isinstance(entry.events_json, dict):
        events = entry.events_json.get("events", [])
    
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
    
    # 转换标签
    tags = []
    if hasattr(entry, 'tags') and entry.tags:
        for tag in entry.tags:
            tags.append(TagResponse(
                id=tag.id,
                name=tag.name,
                tag_type=tag.tag_type,
                color=tag.color,
                icon=tag.icon
            ))
    
    return EntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        content=entry.content,
        emotion=entry.emotion,
        status=entry.status,
        is_visible=entry.is_visible,
        events=events,
        word_count=entry.word_count,
        source_type=entry.source_type,
        images=images,
        tags=tags,
        created_at=entry.created_at,
        updated_at=entry.updated_at
    )


@router.get("/entries", response_model=EntryListResponse, summary="获取当日记录列表")
async def get_entries(
    target_date: Optional[date] = Query(None, description="目标日期，格式：YYYY-MM-DD，默认为今天"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取指定日期的所有记录条目
    
    对应PRD 4.1.1 / 4.1.5 的"记录列表区"和"AI回复区"数据需求
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        journal_service = JournalService(session)
        entries = await journal_service.list_entries_by_date(
            user_id=user_id,
            target_date=target_date
        )
        
        # 转换为响应格式
        entry_responses = [_entry_to_response(entry) for entry in entries]
        
        return EntryListResponse(
            success=True,
            message="获取成功",
            data=entry_responses,
            total=len(entry_responses)
        )
        
    except Exception as e:
        logger.error(f"获取记录列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取记录列表失败: {str(e)}")


@router.post("/entries", response_model=CreateEntryResponse, summary="创建记录")
async def create_entry(
    request: CreateEntryRequest,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    创建新的日记条目
    
    对应PRD 4.1.2, 4.1.3, 4.1.4, 4.1.5 的提交功能
    支持文本输入、语音转文字（前端完成）、图片上传
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        # 验证文本长度
        if len(request.text) > 5000:
            raise HTTPException(status_code=400, detail="文本内容最多5000字")
        
        # 准备图片数据
        images_data = [
            {
                "image_url": img.image_url,
                "is_live_photo": img.is_live_photo,
                "sort_order": img.sort_order
            }
            for img in request.images
        ]
        
        journal_service = JournalService(session)
        entry = await journal_service.create_entry_with_media_and_tags(
            user_id=user_id,
            text=request.text,
            images=images_data,
            tag_ids=request.tag_ids,
            source_type=request.source_type
        )
        
        # 加载关联数据
        await journal_service._load_entry_relations(entry)
        
        # 转换为响应格式
        entry_response = _entry_to_response(entry)
        
        return CreateEntryResponse(
            success=True,
            message="创建成功",
            data=entry_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建记录失败: {str(e)}")


@router.post("/entries/{entry_id}/retry", response_model=RetryEntryResponse, summary="重试发送")
async def retry_entry(
    entry_id: str,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    重试失败的条目
    
    对应PRD 4.1.5 的边界条件处理
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        journal_service = JournalService(session)
        entry = await journal_service.retry_entry(entry_id, user_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="条目不存在或无权限")
        
        # 加载关联数据
        await journal_service._load_entry_relations(entry)
        
        # 转换为响应格式
        entry_response = _entry_to_response(entry)
        
        return RetryEntryResponse(
            success=True,
            message="重试成功",
            data=entry_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试条目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重试条目失败: {str(e)}")


@router.get("/tags", response_model=TagListResponse, summary="获取标签列表")
async def get_tags(
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取当前用户可用的标签列表
    
    对应PRD 4.1.6 的标签管理功能
    免费用户只返回3个默认标签，付费用户包含自定义标签
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        
        journal_service = JournalService(session)
        tags = await journal_service.get_available_tags(user_id)
        
        # 转换为响应格式
        tag_responses = [
            TagResponse(
                id=tag.id,
                name=tag.name,
                tag_type=tag.tag_type,
                color=tag.color,
                icon=tag.icon
            )
            for tag in tags
        ]
        
        return TagListResponse(
            success=True,
            message="获取成功",
            data=tag_responses,
            total=len(tag_responses)
        )
        
    except Exception as e:
        logger.error(f"获取标签列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取标签列表失败: {str(e)}")

