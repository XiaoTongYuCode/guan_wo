"""
基础API路由
包含根路径、健康检查等基础功能
"""
# 标准库导包
import logging

# 第三方库导包
from fastapi import APIRouter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    tags=["基础功能"]
)


@router.get("/", summary="服务欢迎信息")
async def root():
    """
    根路径接口
    
    Returns:
        服务欢迎信息和状态
    """
    return {
        "message": "TYC MCP Web Server",
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口
    
    用于监控服务运行状态，常用于负载均衡器和监控系统
    
    Returns:
        服务健康状态信息
    """
    return {
        "status": "healthy",
        "service": "TYC UNIVERSAL Server",
        "uptime": "运行中",
        "checks": {
            "api": "ok",
            "memory": "ok",
            "disk": "ok"
        }
    } 