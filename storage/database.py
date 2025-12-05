"""Database configuration module."""
# 标准库导包
import logging
from typing import AsyncGenerator

# 第三方库导包  
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# 项目内部导包
from config import settings

# 配置日志
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_database_url() -> str:
    """构建数据库URL"""
    # 从HOST中分离主机和端口
    host_port = settings.DB_HOST
    if ':' in host_port:
        host, port = host_port.split(':')
    else:
        host = host_port
        port = "3306"
    
    # 构建异步MySQL URL
    database_url = f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{host}:{port}/{settings.DB_NAME}"
    return database_url


# 获取数据库URL
DATABASE_URL = get_database_url()
logger.info(f"数据库连接URL: {DATABASE_URL.replace(settings.DB_PASSWORD, '***')}")

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_CONNECTIONS - settings.DB_POOL_SIZE,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=settings.DEBUG,  # 调试模式下显示SQL语句
    echo_pool=settings.DEBUG,  # 调试模式下显示连接池信息
)

# 创建会话工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db():
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表初始化完成")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的异步生成器
    
    这是一个依赖注入函数，可以用于FastAPI的Depends。
    
    Yields:
        AsyncSession: 数据库会话对象
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"数据库会话发生错误: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def cleanup_db():
    """清理数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")
