"""
EntryImageRepository - 条目图片Repository
"""
# 标准库导包
from typing import Optional, List

# 第三方库导包
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.entry_image import EntryImage
from storage.repositories.base import BaseRepository


class EntryImageRepository(BaseRepository[EntryImage]):
    """条目图片Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, EntryImage)
    
    async def get_by_entry_id(
        self,
        entry_id: str,
        order_by_sort: bool = True
    ) -> List[EntryImage]:
        """
        根据条目ID获取所有图片
        
        Args:
            entry_id: 条目ID
            order_by_sort: 是否按sort_order排序
            
        Returns:
            图片列表
        """
        query = select(EntryImage).where(EntryImage.entry_id == entry_id)
        
        if order_by_sort:
            query = query.order_by(EntryImage.sort_order.asc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_upload_status(
        self,
        entry_id: str,
        upload_status: str
    ) -> List[EntryImage]:
        """
        根据上传状态获取图片
        
        Args:
            entry_id: 条目ID
            upload_status: 上传状态（pending/uploading/success/failed）
            
        Returns:
            图片列表
        """
        return await self.query_by_filters(
            filters={"entry_id": entry_id, "upload_status": upload_status},
            order_by="sort_order",
            order_desc=False
        )
    
    async def update_upload_status(
        self,
        image_id: str,
        upload_status: str,
        image_url: Optional[str] = None
    ) -> Optional[EntryImage]:
        """
        更新图片上传状态
        
        Args:
            image_id: 图片ID
            upload_status: 上传状态
            image_url: 图片URL（可选）
            
        Returns:
            更新后的图片实例
        """
        update_data = {"upload_status": upload_status}
        
        if image_url:
            update_data["image_url"] = image_url
        
        return await self.update_by_id(image_id, **update_data)
    
    async def delete_by_entry_id(self, entry_id: str) -> int:
        """
        删除指定条目的所有图片
        
        Args:
            entry_id: 条目ID
            
        Returns:
            删除的图片数量
        """
        images = await self.get_by_entry_id(entry_id)
        count = 0
        
        for image in images:
            if await self.delete_by_id(image.id):
                count += 1
        
        return count

