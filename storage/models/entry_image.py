"""
EntryImage模型 - 条目图片表
"""
# 标准库导包
import uuid
from datetime import datetime
from typing import Optional

# 第三方库导包
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class EntryImage(Base):
    """条目图片表"""
    
    __tablename__ = "entry_images"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="图片URL")
    upload_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="上传状态：pending/uploading/success/failed")
    is_live_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否为Live Photo")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序顺序")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 扩展字段
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="缩略图URL")
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="文件大小，字节")
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="图片宽度")
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="图片高度")
    
    # 关系定义
    entry: Mapped["Entry"] = relationship("Entry", back_populates="images")
    
    def __repr__(self):
        return f"<EntryImage(id={self.id}, entry_id={self.entry_id}, upload_status={self.upload_status})>"

