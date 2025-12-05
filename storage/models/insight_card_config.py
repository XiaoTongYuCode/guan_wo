"""
InsightCardConfig模型 - 洞察配置表（付费功能）
"""
# 标准库导包
import uuid
from datetime import datetime, time
from typing import Optional

# 第三方库导包
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 项目内部导包
from storage.database import Base


class InsightCardConfig(Base):
    """洞察配置表（付费功能）"""
    
    __tablename__ = "insight_card_configs"
    
    # 核心字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="洞察名称")
    time_range: Mapped[str] = mapped_column(String(20), nullable=False, comment="时间范围：daily/weekly/monthly")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="洞察提示词")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序顺序")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 扩展字段
    max_cards_per_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="每个周期最多生成卡片数")
    generation_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True, comment="生成时间点，如05:00")
    
    # 关系定义
    cards: Mapped[list["InsightCard"]] = relationship("InsightCard", back_populates="config")
    
    def __repr__(self):
        return f"<InsightCardConfig(id={self.id}, user_id={self.user_id}, name={self.name})>"

