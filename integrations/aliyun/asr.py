"""
阿里云语音识别占位封装
"""
# 标准库导包
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

# 第三方库导包

# 项目内部导包
from integrations.aliyun import ALIYUN_DEFAULT_REGION

logger = logging.getLogger(__name__)


@dataclass
class AliyunASRConfig:
    """阿里云ASR配置"""
    access_key_id: str = ""
    access_key_secret: str = ""
    app_key: str = ""
    region: str = ALIYUN_DEFAULT_REGION
    endpoint: Optional[str] = None


class AliyunASRClient:
    """阿里云ASR客户端占位实现"""

    def __init__(self, config: AliyunASRConfig):
        self.config = config

    @classmethod
    def from_settings(cls, settings) -> "AliyunASRClient":
        """从全局设置创建客户端"""
        config = AliyunASRConfig(
            access_key_id=getattr(settings, "ALIYUN_ACCESS_KEY_ID", ""),
            access_key_secret=getattr(settings, "ALIYUN_ACCESS_KEY_SECRET", ""),
            app_key=getattr(settings, "ALIYUN_ASR_APP_KEY", ""),
            region=getattr(settings, "ALIYUN_REGION", ALIYUN_DEFAULT_REGION),
            endpoint=getattr(settings, "ALIYUN_ASR_ENDPOINT", None),
        )
        return cls(config)

    async def transcribe(
        self,
        audio_url: str,
        format: str = "wav",
        sample_rate: int = 16000,
        language: str = "zh",
    ) -> Tuple[str, Optional[int]]:
        """
        语音转文字占位方法

        Returns:
            (转写文本, 音频时长秒)
        """
        # 这里只做占位，便于后续接入真实SDK
        logger.info(
            "调用阿里云ASR占位: url=%s, format=%s, sample_rate=%s, language=%s",
            audio_url,
            format,
            sample_rate,
            language,
        )
        placeholder_text = "【占位转写结果】语音识别功能待接入阿里云ASR"
        return placeholder_text, None


