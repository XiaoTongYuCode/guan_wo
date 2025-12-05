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
from sqlalchemy.orm import selectinload

# 项目内部导包
from storage.models.entry import Entry
from storage.models.entry_image import EntryImage
from storage.models.tag import Tag
from storage.repositories.entry_repository import EntryRepository
from storage.repositories.entry_image_repository import EntryImageRepository
from storage.repositories.entry_tag_repository import EntryTagRepository
from storage.repositories.tag_repository import TagRepository
from llm.client import LLMClient

# 配置日志
logger = logging.getLogger(__name__)


class JournalService:
    """日记服务类"""
    
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
    
    async def create_entry_with_media_and_tags(
        self,
        user_id: str,
        text: str,
        images: List[Dict[str, Any]],
        tag_ids: List[str],
        source_type: str = "text"
    ) -> Entry:
        """
        创建条目，保存图片信息和标签关联
        
        Args:
            user_id: 用户ID
            text: 文本内容
            images: 图片列表，每个元素包含 image_url, is_live_photo, sort_order
            tag_ids: 标签ID列表
            source_type: 来源类型（text/voice）
            
        Returns:
            创建的Entry实例
        """
        # 计算字数
        word_count = len(text)
        
        # 创建Entry（状态为sending）
        entry = await self.entry_repo.create(
            user_id=user_id,
            content=text,
            word_count=word_count,
            status="sending",
            source_type=source_type,
            is_visible=True
        )
        
        # 保存图片
        for idx, image_data in enumerate(images):
            await self.image_repo.create(
                entry_id=entry.id,
                image_url=image_data.get("image_url", ""),
                is_live_photo=image_data.get("is_live_photo", False),
                sort_order=image_data.get("sort_order", idx),
                upload_status="success"  # 假设前端已上传成功
            )
        
        # 关联标签
        for tag_id in tag_ids:
            await self.entry_tag_repo.add_tag_to_entry(entry.id, tag_id)
        
        logger.info(f"创建Entry成功: entry_id={entry.id}, user_id={user_id}, word_count={word_count}")
        
        # 异步触发AI分析（不阻塞返回）
        asyncio.create_task(self._analyze_entry_async(entry.id, text))
        
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
            
            # 更新Entry状态和AI结果
            await self.update_entry_status_and_ai_result(
                entry_id=entry_id,
                status="success",
                events=analysis_result.get("events", []),
                emotion=analysis_result.get("emotion", "neutral"),
                tag_names=analysis_result.get("tags", [])
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
                    # 如果不存在，创建系统标签（可选，根据业务需求）
                    logger.warning(f"标签不存在: {tag_name}，跳过自动打标")
                    continue
                auto_tag_ids.append(tag.id)
            
            # 添加自动标签（不覆盖用户手动选择的标签）
            for tag_id in auto_tag_ids:
                await self.entry_tag_repo.add_tag_to_entry(entry_id, tag_id)
        
        logger.info(f"更新Entry AI结果: entry_id={entry_id}, status={status}, emotion={emotion}")
        
        return entry
    
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
        # 加载图片
        images = await self.image_repo.get_by_entry_id(entry.id)
        entry.images = images
        
        # 加载标签
        tags = await self.entry_tag_repo.get_tags_by_entry_id(entry.id)
        entry.tags = tags
    
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
    
    async def get_available_tags(self, user_id: str) -> List[Tag]:
        """
        获取用户可用的标签列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            标签列表（系统标签 + 用户自定义标签）
        """
        tags = await self.tag_repo.get_all_available_tags(user_id, is_enabled=True)
        return tags

