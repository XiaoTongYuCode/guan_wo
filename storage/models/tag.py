"""
Tag模型 - 标签表
"""
# 标准库导包
import uuid
from datetime import datetime
from typing import Optional

# 第三方库导包
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class Tag(Base):
    """标签表"""
    
    __tablename__ = "tags"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="标签名称")
    tag_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型：system/custom")
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="用户ID，自定义标签需要")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 扩展字段
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="标签颜色，用于UI展示")
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="标签图标")
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="标签描述")
    
    # 关系定义
    entry_tags: Mapped[list["EntryTag"]] = relationship("EntryTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name}, tag_type={self.tag_type})>"

