"""
TagRepository - 标签Repository
"""
# 标准库导包
from typing import Optional, List

# 第三方库导包
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.tag import Tag
from storage.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """标签Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Tag)
    
    async def get_system_tags(self, is_enabled: Optional[bool] = None) -> List[Tag]:
        """
        获取系统标签
        
        Args:
            is_enabled: 是否启用（可选）
            
        Returns:
            系统标签列表
        """
        filters = {"tag_type": "system"}
        
        if is_enabled is not None:
            filters["is_enabled"] = is_enabled
        
        return await self.query_by_filters(filters=filters)
    
    async def get_user_custom_tags(
        self,
        user_id: str,
        is_enabled: Optional[bool] = None
    ) -> List[Tag]:
        """
        获取用户自定义标签
        
        Args:
            user_id: 用户ID
            is_enabled: 是否启用（可选）
            
        Returns:
            用户自定义标签列表
        """
        filters = {"tag_type": "custom", "user_id": user_id}
        
        if is_enabled is not None:
            filters["is_enabled"] = is_enabled
        
        return await self.query_by_filters(filters=filters)
    
    async def get_all_available_tags(
        self,
        user_id: str,
        is_enabled: bool = True
    ) -> List[Tag]:
        """
        获取用户所有可用的标签（系统标签 + 自定义标签）
        
        Args:
            user_id: 用户ID
            is_enabled: 是否仅返回启用的标签
            
        Returns:
            标签列表
        """
        conditions = [
            or_(
                Tag.tag_type == "system",
                and_(Tag.tag_type == "custom", Tag.user_id == user_id)
            )
        ]
        
        if is_enabled:
            conditions.append(Tag.is_enabled == True)
        
        query = select(Tag).where(and_(*conditions))
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_name(
        self,
        name: str,
        user_id: Optional[str] = None
    ) -> Optional[Tag]:
        """
        根据名称获取标签
        
        Args:
            name: 标签名称
            user_id: 用户ID（用于自定义标签查询）
            
        Returns:
            标签实例或None
        """
        if user_id:
            # 查询用户的自定义标签
            filters = {"name": name, "tag_type": "custom", "user_id": user_id}
        else:
            # 查询系统标签
            filters = {"name": name, "tag_type": "system"}
        
        results = await self.query_by_filters(filters=filters, limit=1)
        return results[0] if results else None
    
    async def count_user_custom_tags(self, user_id: str) -> int:
        """
        统计用户自定义标签数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            标签数量
        """
        return await self.count(tag_type="custom", user_id=user_id)

