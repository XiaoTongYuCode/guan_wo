"""
基础Repository类
"""
# 标准库导包
from typing import TypeVar, Generic, Optional, List, Dict, Any
from abc import ABC, abstractmethod

# 第三方库导包
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.sql import func

# 项目内部导包
from storage.database import Base

# 泛型类型
ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """基础Repository类，提供通用的CRUD操作"""
    
    def __init__(self, session: AsyncSession, model: type[ModelType]):
        """
        初始化Repository
        
        Args:
            session: 数据库会话
            model: 数据库模型类
        """
        self.session = session
        self.model = model
    
    async def get_by_id(self, id) -> Optional[ModelType]:
        """
        根据ID获取单条记录
        
        Args:
            id: 记录ID（支持int或str类型）
            
        Returns:
            模型实例或None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """
        获取所有记录
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            模型实例列表
        """
        query = select(self.model)
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> ModelType:
        """
        创建新记录
        
        Args:
            **kwargs: 模型字段值
            
        Returns:
            创建的模型实例
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def update_by_id(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        根据ID更新记录
        
        Args:
            id: 记录ID（支持int或str类型）
            **kwargs: 要更新的字段值
            
        Returns:
            更新后的模型实例或None
        """
        # MySQL不支持RETURNING子句，所以先执行UPDATE，然后重新查询
        # 检查记录是否存在
        existing = await self.get_by_id(id)
        if not existing:
            return None
        
        # 执行UPDATE
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
        )
        
        # 刷新会话以获取最新数据
        await self.session.flush()
        
        # 重新查询更新后的记录
        updated_instance = await self.get_by_id(id)
        
        if updated_instance:
            await self.session.refresh(updated_instance)
        
        return updated_instance
    
    async def delete_by_id(self, id: int) -> bool:
        """
        根据ID删除记录
        
        Args:
            id: 记录ID
            
        Returns:
            是否删除成功
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def count(self, **filters) -> int:
        """
        统计记录数量
        
        Args:
            **filters: 过滤条件
            
        Returns:
            记录数量
        """
        query = select(func.count(self.model.id))
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def exists(self, **filters) -> bool:
        """
        检查记录是否存在
        
        Args:
            **filters: 过滤条件
            
        Returns:
            是否存在
        """
        count = await self.count(**filters)
        return count > 0
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """
        构建过滤条件
        
        Args:
            filters: 过滤条件字典
            
        Returns:
            条件列表
        """
        conditions = []
        
        for key, value in filters.items():
            if not hasattr(self.model, key):
                continue
                
            column = getattr(self.model, key)
            
            if isinstance(value, (list, tuple)):
                # IN 条件
                conditions.append(column.in_(value))
            elif isinstance(value, dict):
                # 高级条件（如范围查询）
                for op, val in value.items():
                    if op == 'gt':
                        conditions.append(column > val)
                    elif op == 'gte':
                        conditions.append(column >= val)
                    elif op == 'lt':
                        conditions.append(column < val)
                    elif op == 'lte':
                        conditions.append(column <= val)
                    elif op == 'like':
                        conditions.append(column.like(f"%{val}%"))
                    elif op == 'ne':
                        conditions.append(column != val)
                    else:
                        # 默认等于
                        conditions.append(column == val)
            else:
                # 等于条件
                conditions.append(column == value)
        
        return conditions
    
    async def query_by_filters(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[ModelType]:
        """
        根据过滤条件查询记录
        
        Args:
            filters: 过滤条件字典
            limit: 限制返回数量
            offset: 偏移量
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            模型实例列表
        """
        conditions = self._build_filter_conditions(filters)
        query = select(self.model)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all()) 