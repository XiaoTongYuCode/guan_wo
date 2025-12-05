# 标准库导包
import asyncio
import json
import logging
import threading
from datetime import datetime
from functools import lru_cache

# 第三方库导包
import redis.asyncio as redis
from redis.asyncio.lock import Lock

# 项目内部导包
from config import settings

logger = logging.getLogger(__name__)

# 全局Redis连接池实例
_redis_pool = None
_redis_pool_lock = threading.Lock()

class DummyLock:
    """虚拟锁对象，用于Redis连接失败时的降级处理"""
    async def release(self):
        pass 

def get_redis():
    """获取Redis连接实例，支持连接池重建"""
    global _redis_pool
    
    with _redis_pool_lock:
        if _redis_pool is None:
            logger.info("创建新的Redis连接池...")
            _redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=50,  # 增加最大连接数到50
                socket_timeout=3600 * 24 * 30,  # 增加套接字超时到30天，支持长时间阻塞操作
                socket_connect_timeout=60.0,  # 连接超时
                socket_keepalive=True,  # 保持连接
                socket_keepalive_options={},  # TCP keepalive选项
                health_check_interval=15,  # 减少健康检查间隔，更快发现连接问题
                retry_on_timeout=True,  # 超时重试
                retry_on_error=[ConnectionError, TimeoutError]  # 指定重试的错误类型
            )
            logger.info(f"Redis连接池创建完成，连接地址: {settings.REDIS_URL}")
        
        return redis.Redis(connection_pool=_redis_pool, decode_responses=True)

def reset_redis_pool():
    """重置Redis连接池"""
    global _redis_pool
    
    with _redis_pool_lock:
        if _redis_pool:
            logger.info("关闭现有Redis连接池...")
            # 注意：这里不能直接调用close()，因为它是异步方法
            _redis_pool = None
        logger.info("Redis连接池已重置")

async def set_cache(key: str, value: any):
    """
    设置缓存
    
    参数:
        key: 缓存键
        value: 缓存值，会被转换为JSON字符串
    """
    r = get_redis()
    
    await r.set(key, json.dumps(value))
    
async def get_cache(key: str):
    """
    获取缓存
    
    参数:
        key: 缓存键
    
    返回:
        若缓存存在，返回解析后的值；否则返回None
    """
    r = get_redis()
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


# ========== 聊天会话相关的Redis操作封装 ==========

async def get_chat_session(session_id: str):
    """
    获取聊天会话历史
    
    参数:
        session_id: 会话ID
        
    返回:
        会话历史数据字典，如果不存在返回None
    """
    session_key = f"{settings.REDIS_KEY_PREFIXES['CHAT_SESSION']}{session_id}"
    return await get_cache(session_key)


async def set_chat_session(session_id: str, session_data: dict, ttl: int = None):
    """
    保存聊天会话历史
    
    参数:
        session_id: 会话ID
        session_data: 会话历史数据
        ttl: 过期时间（秒），默认使用settings.WORKFLOW_SESSION_TTL
    """
    if ttl is None:
        ttl = settings.WORKFLOW_SESSION_TTL
    session_key = f"{settings.REDIS_KEY_PREFIXES['CHAT_SESSION']}{session_id}"
    r = get_redis()
    
    # 设置数据并添加过期时间
    await r.setex(session_key, ttl, json.dumps(session_data))
    logger.debug(f"会话 {session_id} 已保存到Redis，TTL: {ttl}秒")


async def get_user_sessions(user_id: str):
    """
    获取用户的会话列表
    
    参数:
        user_id: 用户ID
        
    返回:
        用户会话列表，如果不存在返回空列表
    """
    user_sessions_key = f"{settings.REDIS_KEY_PREFIXES['USER_SESSIONS']}{user_id}"
    sessions = await get_cache(user_sessions_key)
    return sessions if sessions is not None else []


async def set_user_sessions(user_id: str, sessions_data: list, ttl: int = None):
    """
    保存用户的会话列表
    
    参数:
        user_id: 用户ID
        sessions_data: 会话列表数据
        ttl: 过期时间（秒），默认使用settings.WORKFLOW_SESSION_TTL
    """
    if ttl is None:
        ttl = settings.WORKFLOW_SESSION_TTL
    user_sessions_key = f"{settings.REDIS_KEY_PREFIXES['USER_SESSIONS']}{user_id}"
    r = get_redis()
    
    # 设置数据并添加过期时间
    await r.setex(user_sessions_key, ttl, json.dumps(sessions_data))
    logger.debug(f"用户 {user_id} 的会话列表已保存到Redis，会话数量: {len(sessions_data)}")


async def add_session_to_user_list(user_id: str, session_info: dict):
    """
    将新会话添加到用户会话列表中
    
    参数:
        user_id: 用户ID
        session_info: 会话信息字典，应包含 session_id, title, created_time
        
    返回:
        更新后的会话列表
    """
    # 获取现有会话列表
    user_sessions = await get_user_sessions(user_id)
    
    # 检查会话是否已存在
    session_exists = any(
        session.get("session_id") == session_info.get("session_id") 
        for session in user_sessions 
        if isinstance(session, dict)
    )
    
    if not session_exists:
        # 添加到会话列表开头（最新的会话在前）
        user_sessions.insert(0, session_info)
        
        # 保存更新后的会话列表
        await set_user_sessions(user_id, user_sessions)
        logger.info(
            f"会话 {session_info.get('session_id')} 已添加到用户 {user_id} 的会话索引，"
            f"标题: '{session_info.get('title')}'，当前会话总数: {len(user_sessions)}"
        )
    else:
        logger.info(f"会话 {session_info.get('session_id')} 已存在于用户 {user_id} 的会话索引中")
    
    return user_sessions
