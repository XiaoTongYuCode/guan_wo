"""
LLM模块
提供统一的LLM客户端接口，支持多厂商和多模型切换
"""

from .client import LLMClient

__all__ = ["LLMClient"]

