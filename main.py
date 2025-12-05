"""
TYC MCP Web Server 主应用程序

基于FastAPI和Uvicorn的现代Web服务
"""
# 标准库导包
import logging
from contextlib import asynccontextmanager

# 第三方库导包
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 项目内部导包
from config import settings
from storage.database import init_db, cleanup_db
from routers import basic, journal, insights, tag_tracking, flash

# 配置日志
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理
    """
    # 启动时初始化数据库
    try:
        await init_db()
        logger.info("应用程序启动完成")
        yield
    except Exception as e:
        logger.error(f"应用程序启动失败: {str(e)}")
        raise
    finally:
        # 关闭时清理数据库连接
        try:
            await cleanup_db()
            logger.info("应用程序关闭完成")
        except Exception as e:
            logger.error(f"应用程序关闭时发生错误: {str(e)}")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_NAME,
    description="TYC UNIVERSAL Web Server",
    version=settings.APP_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 注册路由
app.include_router(basic.router)
app.include_router(journal.router)
app.include_router(insights.router)
app.include_router(tag_tracking.router)
app.include_router(flash.router)


def main():
    """
    应用程序入口点
    """
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL,
        workers=settings.WORKERS
    )


if __name__ == "__main__":
    main() 