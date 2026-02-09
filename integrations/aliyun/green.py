"""
阿里云内容安全占位封装
"""
# 标准库导包
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

# 第三方库导包

# 项目内部导包
from integrations.aliyun import ALIYUN_DEFAULT_REGION, ALIYUN_DEFAULT_ENDPOINT

logger = logging.getLogger(__name__)


@dataclass
class AliyunGreenConfig:
    """阿里云内容安全配置"""
    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = ALIYUN_DEFAULT_REGION
    endpoint: str = ALIYUN_DEFAULT_ENDPOINT


class AliyunGreenClient:
    """阿里云内容安全客户端占位实现"""

    def __init__(self, config: AliyunGreenConfig):
        self.config = config

    @classmethod
    def from_settings(cls, settings) -> "AliyunGreenClient":
        """从全局设置创建客户端"""
        config = AliyunGreenConfig(
            access_key_id=getattr(settings, "ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=getattr(settings, "ALIYUN_ACCESS_KEY_SECRET", ""),
            region=getattr(settings, "ALIYUN_REGION", ALIYUN_DEFAULT_REGION),
            endpoint=getattr(settings, "ALIYUN_GREEN_ENDPOINT", ALIYUN_DEFAULT_ENDPOINT),
        )
        return cls(config)

    async def check_text(self, content: str) -> Dict[str, Any]:
        """
        文本内容安全占位方法
        Returns:
            {"is_safe": bool, "label": Optional[str], "detail": Optional[str]}
        """
        logger.info("调用阿里云文本内容安全占位，长度=%s", len(content or ""))
        return {"is_safe": True, "label": None, "detail": "stub"}

    async def check_image(self, image_url: str) -> Dict[str, Any]:
        """
        图片内容安全占位方法
        Returns:
            {"is_safe": bool, "label": Optional[str], "detail": Optional[str]}
        """
        logger.info("调用阿里云图片内容安全占位，url=%s", image_url)
        return {"is_safe": True, "label": None, "detail": "stub"}


