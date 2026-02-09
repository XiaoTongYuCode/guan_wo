"""
InsightCardConfigRepository - 洞察配置Repository
"""
# 标准库导包
from typing import Optional, List

# 第三方库导包
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 项目内部导包
from storage.models.insight_card_config import InsightCardConfig
from storage.repositories.base import BaseRepository


class InsightCardConfigRepository(BaseRepository[InsightCardConfig]):
    """洞察配置Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, InsightCardConfig)
    
    async def get_by_user_id(
        self,
        user_id: str,
        is_enabled: Optional[bool] = None,
        order_by_sort: bool = True
    ) -> List[InsightCardConfig]:
        """
        根据用户ID获取洞察配置
        
        Args:
            user_id: 用户ID
            is_enabled: 是否启用（可选）
            order_by_sort: 是否按sort_order排序
            
        Returns:
            洞察配置列表
        """
        filters = {"user_id": user_id}
        
        if is_enabled is not None:
            filters["is_enabled"] = is_enabled
        
        return await self.query_by_filters(
            filters=filters,
            order_by="sort_order" if order_by_sort else None,
            order_desc=False
        )
    
    async def get_by_time_range(
        self,
        user_id: str,
        time_range: str,
        is_enabled: bool = True
    ) -> List[InsightCardConfig]:
        """
        根据时间范围获取洞察配置
        
        Args:
            user_id: 用户ID
            time_range: 时间范围（daily/weekly/monthly）
            is_enabled: 是否仅返回启用的配置
            
        Returns:
            洞察配置列表
        """
        return await self.query_by_filters(
            filters={
                "user_id": user_id,
                "time_range": time_range,
                "is_enabled": is_enabled
            },
            order_by="sort_order",
            order_desc=False
        )
    
    async def get_enabled_configs(self, user_id: str) -> List[InsightCardConfig]:
        """
        获取用户所有启用的洞察配置
        
        Args:
            user_id: 用户ID
            
        Returns:
            启用的洞察配置列表
        """
        return await self.get_by_user_id(user_id, is_enabled=True)
    
    async def count_user_configs(self, user_id: str) -> int:
        """
        统计用户的洞察配置数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            配置数量
        """
        return await self.count(user_id=user_id, is_system=False)
    
    async def update_sort_orders(
        self,
        config_id_order_map: dict[str, int]
    ) -> List[InsightCardConfig]:
        """
        批量更新排序顺序
        
        Args:
            config_id_order_map: 配置ID到排序顺序的映射字典
            
        Returns:
            更新后的配置列表
        """
        updated_configs = []
        
        for config_id, sort_order in config_id_order_map.items():
            config = await self.update_by_id(config_id, sort_order=sort_order)
            if config:
                updated_configs.append(config)
        
        return updated_configs
    
    async def toggle_enabled(self, config_id: str) -> Optional[InsightCardConfig]:
        """
        切换配置的启用状态
        
        Args:
            config_id: 配置ID
            
        Returns:
            更新后的配置实例
        """
        config = await self.get_by_id(config_id)
        
        if config:
            return await self.update_by_id(config_id, is_enabled=not config.is_enabled)
        
        return None
