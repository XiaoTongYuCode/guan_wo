"""
EntryTagRepository - 条目标签关联Repository
"""
# 标准库导包
from typing import List, Optional

# 第三方库导包
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# 项目内部导包
from storage.models.entry_tag import EntryTag
from storage.models.tag import Tag
from storage.repositories.base import BaseRepository


class EntryTagRepository(BaseRepository[EntryTag]):
    """条目标签关联Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, EntryTag)
    
    async def get_by_entry_id(self, entry_id: str) -> List[EntryTag]:
        """
        根据条目ID获取所有标签关联
        
        Args:
            entry_id: 条目ID
            
        Returns:
            标签关联列表
        """
        return await self.query_by_filters(filters={"entry_id": entry_id})
    
    async def get_by_tag_id(self, tag_id: str) -> List[EntryTag]:
        """
        根据标签ID获取所有条目关联
        
        Args:
            tag_id: 标签ID
            
        Returns:
            条目关联列表
        """
        return await self.query_by_filters(filters={"tag_id": tag_id})
    
    async def get_tags_by_entry_id(self, entry_id: str) -> List[Tag]:
        """
        根据条目ID获取所有标签
        
        Args:
            entry_id: 条目ID
            
        Returns:
            标签列表
        """
        query = select(EntryTag).where(
            EntryTag.entry_id == entry_id
        ).options(selectinload(EntryTag.tag))
        
        result = await self.session.execute(query)
        entry_tags = list(result.scalars().all())
        
        return [et.tag for et in entry_tags if et.tag]
    
    async def get_entry_ids_by_tag_id(self, tag_id: str) -> List[str]:
        """
        根据标签ID获取所有条目ID
        
        Args:
            tag_id: 标签ID
            
        Returns:
            条目ID列表
        """
        query = select(EntryTag.entry_id).where(EntryTag.tag_id == tag_id)
        result = await self.session.execute(query)
        return [row[0] for row in result.all()]
    
    async def add_tag_to_entry(
        self,
        entry_id: str,
        tag_id: str
    ) -> Optional[EntryTag]:
        """
        为条目添加标签（如果不存在）
        
        Args:
            entry_id: 条目ID
            tag_id: 标签ID
            
        Returns:
            标签关联实例或None（如果已存在）
        """
        # 检查是否已存在
        existing = await self.query_by_filters(
            filters={"entry_id": entry_id, "tag_id": tag_id},
            limit=1
        )
        
        if existing:
            return existing[0]
        
        # 创建新关联
        return await self.create(entry_id=entry_id, tag_id=tag_id)
    
    async def remove_tag_from_entry(
        self,
        entry_id: str,
        tag_id: str
    ) -> bool:
        """
        从条目移除标签
        
        Args:
            entry_id: 条目ID
            tag_id: 标签ID
            
        Returns:
            是否删除成功
        """
        result = await self.session.execute(
            delete(EntryTag).where(
                and_(
                    EntryTag.entry_id == entry_id,
                    EntryTag.tag_id == tag_id
                )
            )
        )
        return result.rowcount > 0
    
    async def replace_entry_tags(
        self,
        entry_id: str,
        tag_ids: List[str]
    ) -> List[EntryTag]:
        """
        替换条目的所有标签
        
        Args:
            entry_id: 条目ID
            tag_ids: 新的标签ID列表
            
        Returns:
            新的标签关联列表
        """
        # 删除现有标签
        await self.session.execute(
            delete(EntryTag).where(EntryTag.entry_id == entry_id)
        )
        
        # 添加新标签
        new_entry_tags = []
        for tag_id in tag_ids:
            entry_tag = await self.create(entry_id=entry_id, tag_id=tag_id)
            new_entry_tags.append(entry_tag)
        
        return new_entry_tags
    
    async def delete_by_entry_id(self, entry_id: str) -> int:
        """
        删除指定条目的所有标签关联
        
        Args:
            entry_id: 条目ID
            
        Returns:
            删除的关联数量
        """
        result = await self.session.execute(
            delete(EntryTag).where(EntryTag.entry_id == entry_id)
        )
        return result.rowcount
    
    async def delete_by_tag_id(self, tag_id: str) -> int:
        """
        删除指定标签的所有条目关联
        
        Args:
            tag_id: 标签ID
            
        Returns:
            删除的关联数量
        """
        result = await self.session.execute(
            delete(EntryTag).where(EntryTag.tag_id == tag_id)
        )
        return result.rowcount

