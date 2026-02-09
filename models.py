"""
数据模型定义
"""
# 标准库导包
from typing import Optional, Dict, Any, List
from datetime import datetime, date

# 第三方库导包
from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """用户信息模型"""
    mobile: str
    name: Optional[str] = None
    user_id: Optional[str] = None


class SearchParams(BaseModel):
    """聊天服务请求参数模型（保留用于兼容）"""
    query: str
    mode: Optional[str] = 'fast'  # 'fast' 或 'deep'
    session_id: Optional[str] = None


class Message(BaseModel):
    """单条消息模型（保留用于兼容）"""
    role: str  # 'user' | 'assistant' | 'reference'
    content: str
    timestamp: int


class SessionHistory(BaseModel):
    """会话历史模型（保留用于兼容）"""
    user_id: str
    timestamp: int
    session_id: str
    messages: List[Message]
    message_count: int


class SessionHistoryResponse(BaseModel):
    """会话历史响应模型（保留用于兼容）"""
    success: bool
    message: str
    timestamp: int
    session_id: str
    messages: List[Message]
    message_count: int
    user_id: Optional[str] = None


# ========== Journal模块相关模型 ==========

class EntryImageRequest(BaseModel):
    """条目图片请求模型"""
    image_url: str
    is_live_photo: bool = False
    sort_order: int = 0
    upload_status: str = Field(default="success", description="上传状态：pending/uploading/success/failed")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图地址，可选")


class CreateEntryRequest(BaseModel):
    """创建条目请求模型"""
    text: str = Field(default="", max_length=5000, description="文本内容，最多5000字")
    images: List[EntryImageRequest] = Field(default_factory=list, description="图片列表")
    tag_ids: List[str] = Field(default_factory=list, description="标签ID列表")
    source_type: str = Field(default="text", description="来源类型：text/voice")
    audio_url: Optional[str] = Field(default=None, description="语音文件URL，占位用于ASR")
    audio_duration: Optional[int] = Field(default=None, description="语音时长，秒，最大60秒", le=60)
    transcription_text: Optional[str] = Field(default=None, description="客户端已转写文本，可选")


class EntryImageResponse(BaseModel):
    """条目图片响应模型"""
    id: str
    image_url: str
    thumbnail_url: Optional[str] = None
    upload_status: str
    is_live_photo: bool
    sort_order: int


class TagResponse(BaseModel):
    """标签响应模型"""
    id: str
    name: str
    tag_type: str
    color: Optional[str] = None
    icon: Optional[str] = None


class EntryResponse(BaseModel):
    """条目响应模型"""
    id: str
    user_id: str
    content: str
    emotion: Optional[str] = None
    status: str
    is_visible: bool
    events: List[str] = Field(default_factory=list, description="核心事件列表")
    word_count: Optional[int] = None
    source_type: Optional[str] = None
    audio_duration: Optional[int] = None
    share_count: int = 0
    images: List[EntryImageResponse] = Field(default_factory=list)
    tags: List[TagResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EntryListResponse(BaseModel):
    """条目列表响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[EntryResponse]
    total: int


class CreateEntryResponse(BaseModel):
    """创建条目响应模型"""
    success: bool = True
    message: str = "创建成功"
    data: EntryResponse


class RetryEntryResponse(BaseModel):
    """重试条目响应模型"""
    success: bool = True
    message: str = "重试成功"
    data: EntryResponse


class UpdateEntryTagsRequest(BaseModel):
    """更新条目标签请求"""
    tag_ids: List[str] = Field(default_factory=list, description="新的标签ID列表，长度可为0表示清空")


class UpdateEntryTagsResponse(BaseModel):
    """更新条目标签响应"""
    success: bool = True
    message: str = "更新成功"
    data: EntryResponse


class TagListResponse(BaseModel):
    """标签列表响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[TagResponse]
    total: int


class DaySummaryResponse(BaseModel):
    """按日汇总的记录信息"""
    date: str
    count: int
    word_count: int


class CalendarStatsResponse(BaseModel):
    """日历/历史视图的按日汇总响应"""
    success: bool = True
    message: str = "获取成功"
    data: List[DaySummaryResponse]


# ========== Insight模块相关模型 ==========

class InsightCardResponse(BaseModel):
    """洞察卡片响应模型"""
    id: str
    user_id: str
    card_type: str
    content: Dict[str, Any]
    data_start_time: datetime
    data_end_time: datetime
    is_viewed: bool
    is_hidden: bool
    generated_at: datetime
    created_at: datetime
    updated_at: datetime


class InsightCardListResponse(BaseModel):
    """洞察卡片列表响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[InsightCardResponse]
    total: int


class InsightCardDetailResponse(BaseModel):
    """洞察卡片详情响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: InsightCardResponse


class InsightCardConfigResponse(BaseModel):
    """洞察配置响应模型"""
    id: str
    user_id: str
    name: str
    card_type: str
    time_range: str
    prompt: str
    sort_order: int
    is_enabled: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime


class InsightCardConfigListResponse(BaseModel):
    """洞察配置列表响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[InsightCardConfigResponse]
    total: int


class CreateInsightCardConfigRequest(BaseModel):
    """创建洞察配置请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    time_range: str = Field(..., description="时间范围：daily/weekly/monthly")
    prompt: str = Field(..., min_length=1, description="洞察提示词")


class UpdateInsightCardConfigRequest(BaseModel):
    """更新洞察配置请求模型（仅自定义）"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    time_range: Optional[str] = Field(default=None, description="时间范围：daily/weekly/monthly")
    prompt: Optional[str] = Field(default=None, min_length=1, description="洞察提示词")


class ReorderInsightConfigsRequest(BaseModel):
    """洞察配置排序请求模型（仅自定义）"""
    config_ids: List[str] = Field(..., description="新的排序ID列表")


# ========== Tag Tracking模块相关模型 ==========

class HeatmapDataResponse(BaseModel):
    """热力图数据响应模型"""
    date: str
    count: int
    word_count: int


class TagBubbleDataResponse(BaseModel):
    """标签气泡图数据响应模型"""
    tag_id: str
    tag_name: str
    color: Optional[str] = None
    event_count: int


class EmotionDistributionResponse(BaseModel):
    """情绪分布响应模型"""
    positive: int
    neutral: int
    negative: int
    total: int
    positive_percent: float
    neutral_percent: float
    negative_percent: float


class EmotionTrendPointResponse(BaseModel):
    """情绪趋势点响应模型"""
    date: str
    score: float
    positive_count: int
    total_count: int


class TrackingOverviewResponse(BaseModel):
    """追踪概览响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: Dict[str, Any]


class TagTrackingResponse(BaseModel):
    """标签追踪响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: Dict[str, Any]


# ========== Flash Moments模块相关模型 ==========

class FlashMomentResponse(BaseModel):
    """闪光时刻响应模型"""
    id: str
    user_id: str
    content: str
    content_summary: str = Field(..., description="内容摘要（前50字）")
    emotion: str
    share_count: int = 0
    images: List[EntryImageResponse] = Field(default_factory=list)
    created_at: datetime


class FlashMomentListResponse(BaseModel):
    """闪光时刻列表响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[FlashMomentResponse]
    total: int


class FlashMomentDetailResponse(BaseModel):
    """闪光时刻详情响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: EntryResponse
