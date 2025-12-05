"""
流处理器类
用于处理流式响应的累积和保存逻辑
"""
# 标准库导包
import logging
from typing import List, AsyncGenerator

# 项目内部导包
from models import Message
from .response_parser import parse_assistant_response, is_error_response
from ..services import SessionService

# 配置日志
logger = logging.getLogger(__name__)


class StreamHandler:
    """流处理器类"""
    
    def __init__(self, session_id: str):
        """
        初始化流处理器
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.response_chunks: List[str] = []
        self.stream_completed = False
    
    async def process_stream(self, stream_generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """
        处理流式响应，累积数据并在结束时保存
        
        Args:
            stream_generator: 流式响应生成器
            
        Yields:
            str: 流式响应的每个chunk
        """
        try:
            async for chunk in stream_generator:
                if chunk:
                    # 累积chunk用于后续保存
                    self.response_chunks.append(chunk)
                    yield chunk
            
            self.stream_completed = True
            
        except Exception as e:
            logger.error(f"流处理异常: {str(e)}")
            raise
        finally:
            # 流式响应结束后保存assistant回复
            await self._save_assistant_response()
    
    async def _save_assistant_response(self) -> None:
        """
        保存assistant回复到会话历史
        """
        if not self.response_chunks:
            logger.warning("没有响应数据需要保存")
            return
        
        try:
            # 解析响应内容
            assistant_content, reference_message = parse_assistant_response(self.response_chunks)
            
            # 检查是否是错误响应
            if is_error_response(self.response_chunks):
                logger.warning("检测到错误响应，跳过保存")
                return
            
            # 只有在成功完成流式传输或有有效内容时才保存
            if self.stream_completed or (assistant_content and assistant_content.strip()):
                await SessionService.add_assistant_message(
                    session_id=self.session_id,
                    content=assistant_content,
                    reference_message=reference_message
                )
                logger.info(f"assistant回复已保存到会话 {self.session_id}")
            else:
                logger.warning("流式传输未完成且内容无效，跳过保存")
                
        except Exception as e:
            logger.error(f"保存assistant回复异常: {str(e)}")
    
    def add_chunk(self, chunk: str) -> None:
        """
        添加响应chunk
        
        Args:
            chunk: 响应chunk
        """
        if chunk:
            self.response_chunks.append(chunk)
    
    def mark_completed(self) -> None:
        """
        标记流式传输完成
        """
        self.stream_completed = True 