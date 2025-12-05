"""
EntryTag模型 - 条目标签关联表
"""
# 标准库导包
import uuid
from datetime import datetime

# 第三方库导包
from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class EntryTag(Base):
    """条目标签关联表"""
    
    __tablename__ = "entry_tags"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[str] = mapped_column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    entry: Mapped["Entry"] = relationship("Entry", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="entry_tags")
    
    # 唯一索引
    __table_args__ = (
        UniqueConstraint("entry_id", "tag_id", name="uq_entry_tag"),
    )
    
    def __repr__(self):
        return f"<EntryTag(id={self.id}, entry_id={self.entry_id}, tag_id={self.tag_id})>"

