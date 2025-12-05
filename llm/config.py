"""
LLM配置模块
负责解析和验证LLM提供商配置
"""
# 标准库导包
from typing import Dict, Optional

# 第三方库导包
from pydantic import BaseModel

# 项目内部导包
from config import settings


class LLMModelConfig(BaseModel):
    """LLM模型配置"""
    id: str
    name: str


class LLMProviderConfig(BaseModel):
    """LLM提供商配置"""
    api_key: str
    base_url: str
    models: Dict[str, LLMModelConfig]


class LLMConfig(BaseModel):
    """LLM配置"""
    providers: Dict[str, LLMProviderConfig]
    default_provider: str
    default_model_key: str


def load_llm_config() -> LLMConfig:
    """
    从settings加载LLM配置
    
    Returns:
        LLMConfig对象
    """
    providers_raw = settings.LLM_PROVIDERS
    providers = {}
    
    for name, cfg in providers_raw.items():
        providers[name] = LLMProviderConfig(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            models={
                k: LLMModelConfig(**v) 
                for k, v in cfg["models"].items()
            }
        )
    
    return LLMConfig(
        providers=providers,
        default_provider=settings.DEFAULT_LLM_PROVIDER,
        default_model_key=settings.DEFAULT_LLM_MODEL_KEY,
    )


# 全局LLM配置实例
llm_config = load_llm_config()

