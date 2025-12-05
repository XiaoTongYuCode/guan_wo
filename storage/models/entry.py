"""
Entry模型 - 条目/记录表
"""
# 标准库导包
import uuid
from datetime import datetime
from typing import Optional

# 第三方库导包
from sqlalchemy import String, Text, Boolean, Integer, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class Entry(Base):
    """条目/记录表"""
    
    __tablename__ = "entries"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文本内容，最多5000字")
    emotion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="情绪：positive/neutral/negative")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sending", comment="状态：sending/success/failed/violated")
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否可见，内容审核用")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 扩展字段
    events_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="存储1-3个核心事件的JSON数据")
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="字数统计")
    audio_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="语音时长，秒")
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="来源：text/voice")
    
    # 关系定义
    images: Mapped[list["EntryImage"]] = relationship("EntryImage", back_populates="entry", cascade="all, delete-orphan")
    tags: Mapped[list["EntryTag"]] = relationship("EntryTag", back_populates="entry", cascade="all, delete-orphan")
    
    # 复合索引
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Entry(id={self.id}, user_id={self.user_id}, emotion={self.emotion}, status={self.status})>"

