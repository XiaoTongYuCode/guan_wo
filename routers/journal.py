"""
日记路由
提供日记条目的创建、查询、重试等API接口
"""
# 标准库导包
import logging
from datetime import date, timedelta
from typing import Optional

# 第三方库导包
from fastapi import APIRouter, HTTPException, Depends, Query, Header
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
    EntryImageResponse,
    CalendarStatsResponse,
    UpdateEntryTagsRequest,
    UpdateEntryTagsResponse
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
    
    # 转换图片（使用服务层预加载的缓存，避免触发ORM懒加载）
    images = []
    cached_images = getattr(entry, "_images_cache", None)
    if cached_images:
        for img in cached_images:
            images.append(EntryImageResponse(
                id=img.id,
                image_url=img.image_url,
                thumbnail_url=img.thumbnail_url,
                upload_status=img.upload_status,
                is_live_photo=img.is_live_photo,
                sort_order=img.sort_order
            ))
    
    # 转换标签（同样使用缓存）
    tags = []
    cached_tags = getattr(entry, "_tags_cache", None)
    if cached_tags:
        for tag in cached_tags:
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
        audio_duration=entry.audio_duration,
        share_count=getattr(entry, "share_count", 0),
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
        
        # 验证输入：语音或文本至少一项
        if not request.text and not request.audio_url:
            raise HTTPException(status_code=400, detail="文本或语音至少提供一项")
        if len(request.text) > 5000:
            raise HTTPException(status_code=400, detail="文本内容最多5000字")

        if request.audio_duration and request.audio_duration > 60:
            raise HTTPException(status_code=400, detail="语音时长最多60秒")

        if len(request.images) > 9:
            raise HTTPException(status_code=400, detail="图片最多选择9张")

        allowed_status = {"pending", "uploading", "success", "failed"}
        
        # 准备图片数据
        images_data = []
        for img in request.images:
            if img.upload_status not in allowed_status:
                raise HTTPException(status_code=400, detail="图片上传状态不合法")
            images_data.append(
                {
                    "image_url": img.image_url,
                    "is_live_photo": img.is_live_photo,
                    "sort_order": img.sort_order,
                    "upload_status": img.upload_status,
                    "thumbnail_url": img.thumbnail_url
                }
            )

        source_type = request.source_type
        if request.audio_url and source_type != "voice":
            source_type = "voice"
        
        journal_service = JournalService(session)
        entry = await journal_service.create_entry_with_media_and_tags(
            user_id=user_id,
            text=request.text,
            images=images_data,
            tag_ids=request.tag_ids,
            source_type=source_type,
            audio_url=request.audio_url,
            audio_duration=request.audio_duration,
            transcription_text=request.transcription_text
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
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
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
    x_member_tier: str = Header(default="free", alias="X-Member-Tier"),
    session: AsyncSession = Depends(get_session)
):
    """
    获取当前用户可用的标签列表
    
    对应PRD 4.1.6 的标签管理功能
    免费用户只返回3个默认标签，付费用户包含自定义标签
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        is_paid_user = x_member_tier.lower() in {"paid", "pro", "vip"}
        
        journal_service = JournalService(session)
        tags = await journal_service.get_available_tags(user_id, is_paid_user=is_paid_user)
        
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


@router.post("/entries/{entry_id}/tags", response_model=UpdateEntryTagsResponse, summary="更新条目标签")
async def update_entry_tags(
    entry_id: str,
    request: UpdateEntryTagsRequest,
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    替换指定条目的标签列表，供前端标签面板使用
    """
    try:
        user_id = user_info.user_id or user_info.mobile
        journal_service = JournalService(session)
        entry = await journal_service.replace_entry_tags(entry_id, user_id, request.tag_ids)

        if not entry:
            raise HTTPException(status_code=404, detail="条目不存在或无权限")

        await journal_service._load_entry_relations(entry)
        entry_response = _entry_to_response(entry)

        return UpdateEntryTagsResponse(
            success=True,
            message="更新成功",
            data=entry_response
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新条目标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新条目标签失败: {str(e)}")


@router.get("/history", response_model=EntryListResponse, summary="按日期范围获取历史记录")
async def get_history_entries(
    start_date: date = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: date = Query(..., description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100, description="每次返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    emotion: Optional[str] = Query(None, description="情绪过滤：positive/neutral/negative"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取指定日期范围内的历史记录列表（支持分页）。
    用于日历/历史视图的列表展示。
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能晚于 end_date")

    try:
        user_id = user_info.user_id or user_info.mobile
        journal_service = JournalService(session)
        entries = await journal_service.list_entries_by_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            emotion=emotion,
            limit=limit,
            offset=offset
        )
        entry_responses = [_entry_to_response(entry) for entry in entries]
        total_count = await journal_service.count_entries_by_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            emotion=emotion
        )

        return EntryListResponse(
            success=True,
            message="获取成功",
            data=entry_responses,
            total=total_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.get("/calendar", response_model=CalendarStatsResponse, summary="获取日历视图统计")
async def get_calendar_stats(
    year: int = Query(..., ge=1970, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    user_info: UserInfo = Depends(get_current_user_or_mock),
    session: AsyncSession = Depends(get_session)
):
    """
    获取指定年月的日级统计（用于日历着色/计数）。
    """
    try:
        # 计算当月起止
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        user_id = user_info.user_id or user_info.mobile
        journal_service = JournalService(session)
        stats = await journal_service.get_daily_stats(user_id, start_date, end_date)

        return CalendarStatsResponse(
            success=True,
            message="获取成功",
            data=stats
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日历统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取日历统计失败: {str(e)}")

