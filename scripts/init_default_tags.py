"""
初始化系统默认标签的脚本
"""
# 标准库导包
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 项目内部导包
from storage import get_session, cleanup_db
from storage.repositories import TagRepository


# 系统默认标签配置
DEFAULT_TAGS = [
    {
        "name": "学习工作",
        "tag_type": "system",
        "color": "#4A90E2",
        "icon": "work",
        "description": "工作、学习相关的记录"
    },
    {
        "name": "社交",
        "tag_type": "system",
        "color": "#F5A623",
        "icon": "people",
        "description": "社交活动、人际关系相关"
    },
    {
        "name": "健康",
        "tag_type": "system",
        "color": "#7ED321",
        "icon": "health",
        "description": "健康、运动、饮食相关"
    }
]


async def init_default_tags():
    """初始化系统默认标签"""
    print("开始初始化系统默认标签...")
    
    async for session in get_session():
        try:
            tag_repo = TagRepository(session)
            
            created_count = 0
            skipped_count = 0
            
            for tag_data in DEFAULT_TAGS:
                # 检查标签是否已存在
                existing_tag = await tag_repo.get_by_name(tag_data["name"])
                
                if existing_tag:
                    print(f"  - 跳过已存在的标签: {tag_data['name']}")
                    skipped_count += 1
                    continue
                
                # 创建新标签
                tag = await tag_repo.create(**tag_data)
                print(f"  ✓ 创建标签: {tag.name} (ID: {tag.id})")
                created_count += 1
            
            print(f"\n完成！创建了 {created_count} 个标签，跳过了 {skipped_count} 个已存在的标签。")
            return 0
            
        except Exception as e:
            print(f"✗ 初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


async def main():
    """主函数"""
    try:
        exit_code = await init_default_tags()
        return exit_code
    finally:
        # 清理数据库连接
        await cleanup_db()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

