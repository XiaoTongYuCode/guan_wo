"""
会话管理服务类
处理聊天会话的创建、获取、更新等业务逻辑
"""
# 标准库导包
import logging
import time
import uuid
from typing import Optional

# 项目内部导包
from models import SessionHistory, Message, UserInfo
from redis_client import (
    get_chat_session,
    set_chat_session,
    add_session_to_user_list
)

# 配置日志
logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务类"""

    @staticmethod
    async def get_or_create_session(
        session_id: Optional[str], 
        user_info: UserInfo,
        first_message_content: str
    ) -> tuple[SessionHistory, bool, str]:
        """
        获取现有会话或创建新会话
        
        Args:
            session_id: 会话ID，如果为None则创建新会话
            user_info: 用户信息
            first_message_content: 第一条消息内容（用于生成会话标题）
            
        Returns:
            tuple[SessionHistory, bool, str]: (会话历史, 是否是新会话, 最终的会话ID)
        """
        current_time = int(time.time())
        user_id = user_info.user_id or user_info.mobile
        actual_session_id = session_id or str(uuid.uuid4())
        is_new_session = False

        # 尝试获取现有会话历史
        session_history = None
        if session_id:
            try:
                session_data = await get_chat_session(session_id)
                if session_data:
                    session_history = SessionHistory(**session_data)
                    logger.info(f"找到现有会话 {session_id}，历史消息数: {len(session_history.messages)}")
            except Exception as e:
                logger.warning(f"获取会话历史失败: {str(e)}")

        # 如果没有现有会话，创建新会话
        if not session_history:
            session_history = SessionHistory(
                user_id=user_id,
                timestamp=current_time,
                session_id=actual_session_id,
                messages=[],
                message_count=0
            )
            is_new_session = True
            logger.info(f"创建新会话 {actual_session_id}")

        return session_history, is_new_session, actual_session_id

    @staticmethod
    async def add_user_message(
        session_history: SessionHistory, 
        content: str
    ) -> None:
        """
        向会话历史添加用户消息
        
        Args:
            session_history: 会话历史对象
            content: 消息内容
        """
        current_time = int(time.time())
        user_message = Message(
            role="user",
            content=content,
            timestamp=current_time
        )
        
        session_history.messages.append(user_message)
        session_history.message_count = len(session_history.messages)
        session_history.timestamp = current_time

    @staticmethod
    async def add_assistant_message(
        session_id: str,
        content: str,
        reference_message: Optional[Message] = None
    ) -> None:
        """
        向会话历史添加助手消息
        
        Args:
            session_id: 会话ID
            content: 助手回复内容
            reference_message: 可选的参考信息消息
        """
        try:
            # 重新获取会话历史并更新
            session_data = await get_chat_session(session_id)
            if session_data:
                updated_session = SessionHistory(**session_data)

                # 添加assistant消息
                assistant_message = Message(
                    role="assistant",
                    content=content,
                    timestamp=int(time.time())
                )
                updated_session.messages.append(assistant_message)

                # 如果有reference消息，也添加到会话历史
                if reference_message:
                    updated_session.messages.append(reference_message)
                    logger.info(f"reference消息已添加到会话 {session_id}")

                updated_session.message_count = len(updated_session.messages)
                updated_session.timestamp = int(time.time())

                await set_chat_session(session_id, updated_session.dict())
                logger.info(f"assistant回复已保存到会话 {session_id}，总消息数: {updated_session.message_count}")
        except Exception as e:
            logger.error(f"保存assistant回复失败: {str(e)}")
            raise

    @staticmethod
    async def save_session(session_id: str, session_history: SessionHistory) -> None:
        """
        保存会话历史到Redis
        
        Args:
            session_id: 会话ID
            session_history: 会话历史对象
        """
        try:
            await set_chat_session(session_id, session_history.dict())
            logger.info(f"会话历史已更新，当前消息数: {session_history.message_count}")
        except Exception as e:
            logger.error(f"保存会话历史失败: {str(e)}")
            raise

    @staticmethod
    async def register_new_session(
        user_id: str, 
        session_id: str, 
        first_message_content: str
    ) -> None:
        """
        注册新会话到用户会话索引
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            first_message_content: 第一条消息内容（用于生成标题）
        """
        try:
            current_time = int(time.time())
            # 创建会话信息字典，使用第一条用户消息作为title
            title = first_message_content[:10] + ("..." if len(first_message_content) > 10 else "")
            session_info = {
                "session_id": session_id,
                "title": title,
                "created_time": current_time
            }

            # 使用封装的函数添加会话到用户会话列表
            await add_session_to_user_list(user_id, session_info)
            logger.info(f"新会话 {session_id} 已注册到用户 {user_id} 的会话索引")
        except Exception as e:
            logger.error(f"更新用户会话索引失败: {str(e)}")
            raise 