"""
LLM客户端模块
基于AsyncOpenAI封装统一的LLM调用接口
"""
# 标准库导包
import json
import logging
from typing import Optional, List, Dict, Any

# 第三方库导包
from openai import AsyncOpenAI
import json_repair

# 项目内部导包
from .config import llm_config, LLMConfig
from prompt import ENTRY_ANALYSIS_SYSTEM_PROMPT, ENTRY_ANALYSIS_USER_PROMPT

# 配置日志
logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端，支持多厂商和多模型切换"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置，如果为None则使用全局配置
        """
        self._config = config or llm_config
        self._clients: Dict[tuple[str, str], AsyncOpenAI] = {}
    
    def _get_client(self, provider: str, model_key: str) -> tuple[AsyncOpenAI, str]:
        """
        获取指定提供商和模型的客户端
        
        Args:
            provider: 提供商名称
            model_key: 模型键
            
        Returns:
            (AsyncOpenAI客户端, 模型ID)元组
            
        Raises:
            ValueError: 如果提供商或模型不存在
        """
        if provider not in self._config.providers:
            raise ValueError(f"提供商 '{provider}' 不存在")
        
        cfg = self._config.providers[provider]
        
        if model_key not in cfg.models:
            raise ValueError(f"模型键 '{model_key}' 在提供商 '{provider}' 中不存在")
        
        model_cfg = cfg.models[model_key]
        cache_key = (provider, model_key)
        
        # 使用缓存避免重复创建客户端
        if cache_key not in self._clients:
            self._clients[cache_key] = AsyncOpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
            )
            logger.info(f"创建LLM客户端: provider={provider}, model={model_cfg.name}")
        
        return self._clients[cache_key], model_cfg.id
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        model_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            provider: 提供商名称，如果为None则使用默认提供商
            model_key: 模型键，如果为None则使用默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大token数
            
        Returns:
            AI回复内容
            
        Raises:
            ValueError: 如果提供商或模型不存在
            Exception: 如果API调用失败
        """
        provider = provider or self._config.default_provider
        model_key = model_key or self._config.default_model_key
        
        client, model_id = self._get_client(provider, model_key)
        
        try:
            logger.debug(f"发送LLM请求: provider={provider}, model={model_id}")
            response = await client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            
            content = response.choices[0].message.content or ""
            logger.debug(f"LLM响应长度: {len(content)} 字符")
            return content
            
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise
    
    async def analyze_entry(
        self,
        content: str,
        provider: Optional[str] = None,
        model_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        分析日记条目，提取事件、情绪和标签
        
        Args:
            content: 日记内容
            provider: 提供商名称
            model_key: 模型键
            
        Returns:
            包含events、emotion、tags的字典
        """
        system_prompt = ENTRY_ANALYSIS_SYSTEM_PROMPT
        user_prompt = ENTRY_ANALYSIS_USER_PROMPT.format(content=content)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response_text = await self.chat(
            messages=messages,
            provider=provider,
            model_key=model_key,
            temperature=0.3,  # 降低温度以获得更稳定的分析结果
        )
        
        # 尝试解析JSON响应
        try:
            # 若存在 Markdown 的 ```json 代码块，则尝试提取其中的内容
            if "```json" in response_text:
                response_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            
            result = json_repair.loads(response_text)
            
            # 验证和规范化结果
            events = result.get("events", [])
            if isinstance(events, str):
                events = [events]
            events = events[:3]  # 最多3个事件
            
            emotion = result.get("emotion", "neutral")
            if emotion not in ["positive", "neutral", "negative"]:
                emotion = "neutral"
            
            tags = result.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            tags = tags[:3]  # 最多3个标签
            
            return {
                "events": events,
                "emotion": emotion,
                "tags": tags
            }
            
        except json.JSONDecodeError:
            logger.warning(f"LLM返回的JSON解析失败，使用默认值。响应: {response_text}")
            # 如果解析失败，返回默认值
            return {
                "events": [content[:50] + "..." if len(content) > 50 else content],
                "emotion": "neutral",
                "tags": []
            }

