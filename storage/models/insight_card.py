"""
InsightCard模型 - 洞察卡片表
"""
# 标准库导包
import uuid
from datetime import datetime
from typing import Optional

# 第三方库导包
from sqlalchemy import String, Boolean, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class InsightCard(Base):
    """洞察卡片表"""
    
    __tablename__ = "insight_cards"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    card_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="卡片类型：daily_affirmation/weekly_emotion_map/weekly_gratitude_list/custom")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="卡片内容，存储图表数据、文字等")
    data_start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="数据源开始时间")
    data_end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="数据源结束时间")
    is_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已查看")
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已隐藏")
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="生成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 扩展字段
    config_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("insight_card_configs.id", ondelete="SET NULL"), nullable=True, comment="关联InsightCardConfig，自定义卡片用")
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分享次数")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="查看次数")
    
    # 关系定义
    config: Mapped[Optional["InsightCardConfig"]] = relationship("InsightCardConfig", back_populates="cards")
    
    # 复合索引
    __table_args__ = (
        Index("idx_user_hidden", "user_id", "is_hidden"),
    )
    
    def __repr__(self):
        return f"<InsightCard(id={self.id}, user_id={self.user_id}, card_type={self.card_type})>"

