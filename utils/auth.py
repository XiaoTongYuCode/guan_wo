"""
认证工具
提供简单的用户标识功能（开发阶段）
"""
# 标准库导包
from typing import Optional

# 第三方库导包
from fastapi import Header, HTTPException

# 项目内部导包
from models import UserInfo


async def get_current_user_or_mock(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> UserInfo:
    """
    获取当前用户（开发阶段使用）
    
    优先从Header中获取X-User-Id，如果没有则返回mock用户
    
    Args:
        x_user_id: X-User-Id header值
        
    Returns:
        UserInfo对象
    """
    if x_user_id:
        return UserInfo(
            user_id=x_user_id,
            mobile=x_user_id,  # 开发阶段用user_id作为mobile
            name=None
        )
    
    # 开发阶段默认返回mock用户
    return UserInfo(
        user_id="mock_user_001",
        mobile="mock_user_001",
        name="Mock User"
    )

