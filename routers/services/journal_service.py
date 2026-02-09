"""
日记服务类
处理日记条目的创建、查询、更新等业务逻辑
"""
# 标准库导包
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

# 第三方库导包
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from config import settings
from integrations.aliyun.asr import AliyunASRClient
from integrations.aliyun.green import AliyunGreenClient
from llm.client import LLMClient
from storage.models.entry import Entry
from storage.models.tag import Tag
from storage.repositories.entry_repository import EntryRepository
from storage.repositories.entry_image_repository import EntryImageRepository
from storage.repositories.entry_tag_repository import EntryTagRepository
from storage.repositories.tag_repository import TagRepository

# 配置日志
logger = logging.getLogger(__name__)


class JournalService:
    """日记服务类"""
    
    DEFAULT_TAG_ALIASES = {
        "学习工作": {"学习", "工作", "职场", "学习工作"},
        "社交": {"社交", "朋友", "家庭", "同事"},
        "健康": {"健康", "运动", "锻炼", "睡眠"},
    }
    FREE_TAG_LIMIT = 3
    
    def __init__(self, session: AsyncSession):
        """
        初始化日记服务
        
        Args:
            session: 数据库会话
        """
        self.session = session
        self.entry_repo = EntryRepository(session)
        self.image_repo = EntryImageRepository(session)
        self.tag_repo = TagRepository(session)
        self.entry_tag_repo = EntryTagRepository(session)
        self.llm_client = LLMClient()
        self.asr_client = AliyunASRClient.from_settings(settings)
        self.green_client = AliyunGreenClient.from_settings(settings)
    
    async def create_entry_with_media_and_tags(
        self,
        user_id: str,
        text: str,
        images: List[Dict[str, Any]],
        tag_ids: List[str],
        source_type: str = "text",
        audio_url: Optional[str] = None,
        audio_duration: Optional[int] = None,
        transcription_text: Optional[str] = None
    ) -> Entry:
        """
        创建条目，保存图片信息和标签关联
        
        Args:
            user_id: 用户ID
            text: 文本内容
            images: 图片列表，每个元素包含 image_url, is_live_photo, sort_order
            tag_ids: 标签ID列表
            source_type: 来源类型（text/voice）
            audio_url: 语音文件URL
            audio_duration: 语音时长（秒）
            transcription_text: 客户端已转写文本
            
        Returns:
            创建的Entry实例
        """
        content_text = (text or "").strip()
        
        # 语音占位处理：优先使用已有转写，其次触发占位ASR
        if source_type == "voice":
            if not content_text and transcription_text:
                content_text = transcription_text.strip()
            if not content_text and audio_url:
                try:
                    asr_text, detected_duration = await self.asr_client.transcribe(audio_url)
                    content_text = asr_text.strip()
                    if not audio_duration and detected_duration:
                        audio_duration = detected_duration
                except Exception as asr_error:
                    logger.warning("语音转写失败，使用空文本继续: %s", str(asr_error))
                    content_text = content_text or ""
        
        # 校验文本长度
        if len(content_text) > 5000:
            raise ValueError("文本内容最多5000字")
        
        word_count = len(content_text)
        
        # 内容安全检查（占位）
        safety = await self._check_content_safety(content_text, images)
        is_visible = safety.get("is_safe", True)
        status = "sending" if is_visible else "violated"
        
        # 创建Entry（状态依据安全检查）
        entry = await self.entry_repo.create(
            user_id=user_id,
            content=content_text,
            word_count=word_count,
            status=status,
            source_type=source_type,
            is_visible=is_visible,
            audio_duration=audio_duration
        )
        
        # 保存图片
        for idx, image_data in enumerate(images):
            await self.image_repo.create(
                entry_id=entry.id,
                image_url=image_data.get("image_url", ""),
                thumbnail_url=image_data.get("thumbnail_url"),
                is_live_photo=image_data.get("is_live_photo", False),
                sort_order=image_data.get("sort_order", idx),
                upload_status=image_data.get("upload_status", "success")
            )
        
        # 关联标签
        for tag_id in tag_ids:
            await self.entry_tag_repo.add_tag_to_entry(entry.id, tag_id)
        
        logger.info(f"创建Entry成功: entry_id={entry.id}, user_id={user_id}, word_count={word_count}")
        
        # 异步触发AI分析（不阻塞返回），违规内容不分析
        if status == "sending":
            asyncio.create_task(self._analyze_entry_async(entry.id, content_text))
        
        return entry
    
    async def _analyze_entry_async(self, entry_id: str, content: str):
        """
        异步分析条目（后台任务）
        
        Args:
            entry_id: 条目ID
            content: 条目内容
        """
        try:
            logger.info(f"开始AI分析: entry_id={entry_id}")
            
            # 调用LLM分析
            analysis_result = await self.llm_client.analyze_entry(content)
            normalized_tags = self._normalize_tags(analysis_result.get("tags", []))
            normalized_emotion = self._normalize_emotion(analysis_result.get("emotion", "neutral"))
            
            # 更新Entry状态和AI结果
            await self.update_entry_status_and_ai_result(
                entry_id=entry_id,
                status="success",
                events=analysis_result.get("events", []),
                emotion=normalized_emotion,
                tag_names=normalized_tags
            )
            
            logger.info(f"AI分析完成: entry_id={entry_id}, emotion={analysis_result.get('emotion')}")
            
        except Exception as e:
            logger.error(f"AI分析失败: entry_id={entry_id}, error={str(e)}")
            # 分析失败时，将状态设为failed
            await self.entry_repo.update_by_id(
                entry_id,
                status="failed"
            )
    
    async def update_entry_status_and_ai_result(
        self,
        entry_id: str,
        status: str,
        events: List[str],
        emotion: str,
        tag_names: List[str]
    ) -> Optional[Entry]:
        """
        更新条目状态和AI分析结果
        
        Args:
            entry_id: 条目ID
            status: 状态（success/failed）
            events: 核心事件列表
            emotion: 情绪（positive/neutral/negative）
            tag_names: 标签名称列表（用于自动打标）
            
        Returns:
            更新后的Entry实例
        """
        # 更新Entry基本信息
        update_data = {
            "status": status,
            "emotion": emotion,
            "events_json": {"events": events}
        }
        
        entry = await self.entry_repo.update_by_id(entry_id, **update_data)
        
        if not entry:
            return None
        
        # 处理自动标签
        if tag_names:
            # 查找或创建标签
            auto_tag_ids = []
            for tag_name in tag_names:
                # 先查找系统标签
                tag = await self.tag_repo.get_by_name(tag_name)
                if not tag:
                    # 如果不存在，自动创建对应的系统标签，避免打标失败
                    logger.info(f"系统标签不存在，自动创建: {tag_name}")
                    tag = await self.tag_repo.create(
                        name=tag_name,
                        tag_type="system",
                        user_id=None,
                        is_enabled=True,
                    )
                auto_tag_ids.append(tag.id)
            
            # 添加自动标签（不覆盖用户手动选择的标签）
            for tag_id in auto_tag_ids:
                await self.entry_tag_repo.add_tag_to_entry(entry_id, tag_id)
        
        logger.info(f"更新Entry AI结果: entry_id={entry_id}, status={status}, emotion={emotion}")
        
        return entry
    
    async def _check_content_safety(
        self,
        content: str,
        images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        内容安全占位检查
        """
        result = {"is_safe": True, "violations": []}
        
        try:
            if content:
                text_res = await self.green_client.check_text(content)
                if not text_res.get("is_safe", True):
                    result["is_safe"] = False
                    result["violations"].append({"type": "text", **text_res})
            
            for img in images:
                image_url = img.get("image_url") or ""
                if not image_url:
                    continue
                img_res = await self.green_client.check_image(image_url)
                if not img_res.get("is_safe", True):
                    result["is_safe"] = False
                    result["violations"].append({"type": "image", "url": image_url, **img_res})
        
        except Exception as err:
            # 内容安全不可用时，放行但记录
            logger.warning("内容安全检查失败，默认放行: %s", str(err))
        
        return result
    
    def _normalize_tags(self, tag_names: List[str]) -> List[str]:
        """
        将LLM标签映射到PRD默认标签集
        """
        normalized: set[str] = set()
        for name in tag_names or []:
            clean = (name or "").strip()
            for canonical, aliases in self.DEFAULT_TAG_ALIASES.items():
                if clean in aliases:
                    normalized.add(canonical)
        return list(normalized)[:3]
    
    def _normalize_emotion(self, emotion: str) -> str:
        """校准情绪字段"""
        if emotion in {"positive", "neutral", "negative"}:
            return emotion
        return "neutral"
    
    async def list_entries_by_date(
        self,
        user_id: str,
        target_date: Optional[date] = None
    ) -> List[Entry]:
        """
        按日期获取条目列表
        
        Args:
            user_id: 用户ID
            target_date: 目标日期，如果为None则使用今天
            
        Returns:
            Entry列表（按创建时间倒序）
        """
        if target_date is None:
            target_date = date.today()
        
        # 计算时间范围（当天的00:00:00到23:59:59）
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # 加载关联数据
        for entry in entries:
            await self._load_entry_relations(entry)
        
        return entries

    async def list_entries_by_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        emotion: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Entry]:
        """
        按日期范围获取条目列表（支持分页）
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())

        entries = await self.entry_repo.get_by_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            emotion=emotion,
            limit=limit,
            offset=offset
        )

        for entry in entries:
            await self._load_entry_relations(entry)

        return entries

    async def get_daily_stats(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取指定日期范围内的日级统计
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        return await self.entry_repo.get_daily_stats(user_id, start_time, end_time)

    async def count_entries_by_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        emotion: Optional[str] = None
    ) -> int:
        """
        统计日期范围内的记录数量
        """
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        return await self.entry_repo.count_by_user_and_date_range(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            emotion=emotion
        )
    
    async def get_entry_detail(self, entry_id: str, user_id: str) -> Optional[Entry]:
        """
        获取条目详情
        
        Args:
            entry_id: 条目ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            Entry实例或None
        """
        entry = await self.entry_repo.get_by_id(entry_id)
        
        if not entry:
            return None
        
        # 验证权限
        if entry.user_id != user_id:
            return None
        
        # 加载关联数据
        await self._load_entry_relations(entry)
        
        return entry
    
    async def _load_entry_relations(self, entry: Entry):
        """
        加载Entry的关联数据（图片、标签）
        
        Args:
            entry: Entry实例
        """
        # 加载图片（避免触发ORM懒加载，在实例上缓存为普通属性）
        images = await self.image_repo.get_by_entry_id(entry.id)
        setattr(entry, "_images_cache", images)
        
        # 加载标签（同样走缓存字段）
        tags = await self.entry_tag_repo.get_tags_by_entry_id(entry.id)
        setattr(entry, "_tags_cache", tags)
    
    async def retry_entry(self, entry_id: str, user_id: str) -> Optional[Entry]:
        """
        重试失败的条目
        
        Args:
            entry_id: 条目ID
            user_id: 用户ID
            
        Returns:
            更新后的Entry实例
        """
        entry = await self.entry_repo.get_by_id(entry_id)
        
        if not entry or entry.user_id != user_id:
            return None
        
        if entry.status != "failed":
            logger.warning(f"Entry状态不是failed，无法重试: entry_id={entry_id}, status={entry.status}")
            return entry
        
        # 重置状态为sending
        entry = await self.entry_repo.update_by_id(entry_id, status="sending")
        
        if entry:
            # 异步触发AI分析
            asyncio.create_task(self._analyze_entry_async(entry.id, entry.content))
        
        return entry
    
    async def get_available_tags(self, user_id: str, is_paid_user: bool = False) -> List[Tag]:
        """
        获取用户可用的标签列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            标签列表（系统标签 + 用户自定义标签）
        """
        tags = await self.tag_repo.get_all_available_tags(user_id, is_enabled=True)
        if is_paid_user:
            return tags

        # 免费用户：仅返回系统标签的前三个
        system_tags = [tag for tag in tags if tag.tag_type == "system"]
        return system_tags[: self.FREE_TAG_LIMIT]

    async def replace_entry_tags(
        self,
        entry_id: str,
        user_id: str,
        tag_ids: List[str]
    ) -> Optional[Entry]:
        """
        替换指定条目的标签（需校验归属）
        """
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry or entry.user_id != user_id:
            return None

        available_tags = await self.tag_repo.get_all_available_tags(user_id, is_enabled=True)
        allowed_tag_ids = {tag.id for tag in available_tags}
        filtered_tag_ids = [tid for tid in tag_ids if tid in allowed_tag_ids]

        await self.entry_tag_repo.replace_entry_tags(entry_id, filtered_tag_ids)
        await self._load_entry_relations(entry)
        return entry

