"""
响应解析工具函数
用于解析SSE流式响应中的assistant回复内容
"""
# 标准库导包
import json
import logging
import time
from typing import Optional, Tuple

# 项目内部导包
from models import Message

# 配置日志
logger = logging.getLogger(__name__)


def parse_assistant_response(response_chunks: list[str]) -> Tuple[str, Optional[Message]]:
    """
    解析assistant回复的流式响应数据
    
    Args:
        response_chunks: 流式响应的chunk列表
        
    Returns:
        Tuple[str, Optional[Message]]: (解析后的内容, 可选的reference消息)
    """
    if not response_chunks:
        return "", None
    
    # 将所有chunks合并成完整的响应
    full_response = "".join(response_chunks)
    
    # 初始化返回值
    assistant_content = full_response
    reference_message = None
    
    # 检查是否包含SSE格式的数据
    if "data: " in assistant_content:
        try:
            lines = assistant_content.split('\n')
            content_parts = []
            
            for line in lines:
                if line.startswith('data: '):
                    data_str = line[6:]  # 移除'data: '前缀
                    
                    # 跳过空行和结束标记
                    if not data_str or not data_str.strip() or data_str == '[DONE]':
                        continue
                    
                    try:
                        data_obj = json.loads(data_str)
                        
                        if isinstance(data_obj, dict):
                            # 只处理 type="summary" 的对象
                            if data_obj.get('type') == 'summary':
                                # 累积summary类型的content
                                if 'content' in data_obj:
                                    content_parts.append(data_obj['content'])
                                
                                # 检查是否是最终的summary且包含reference
                                if (data_obj.get('is_final') is True and
                                    'metadata' in data_obj and
                                    'reference' in data_obj['metadata']):
                                    # 创建reference消息
                                    reference_content = json.dumps(
                                        data_obj['metadata']['reference'],
                                        ensure_ascii=False,
                                        indent=2
                                    )
                                    reference_message = Message(
                                        role="reference",
                                        content=reference_content,
                                        timestamp=int(time.time())
                                    )
                                    logger.info("解析到reference信息")
                        
                        elif isinstance(data_obj, str):
                            # 如果直接是字符串，也添加到content_parts
                            content_parts.append(data_obj)
                    
                    except json.JSONDecodeError:
                        # JSON解析失败时，保留原始字符串
                        content_parts.append(data_str)
            
            # 如果解析到了有效内容，使用解析后的内容
            if content_parts:
                assistant_content = "".join(content_parts)
            
        except Exception as e:
            logger.warning(f"解析SSE响应失败，使用原始响应: {str(e)}")
            assistant_content = full_response
    
    return assistant_content, reference_message


def is_error_response(response_chunks: list[str]) -> bool:
    """
    检查响应是否包含错误信息
    
    Args:
        response_chunks: 流式响应的chunk列表
        
    Returns:
        bool: 是否包含错误信息
    """
    if not response_chunks:
        return False
    
    full_response = "".join(response_chunks)
    
    # 检查是否包含错误标记
    return (
        'data: {"error"' in full_response or
        '"error":' in full_response or
        full_response.startswith('data: {"error"')
    ) 