"""
初始化日记洞察系统数据表的脚本
"""
# 标准库导包
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 第三方库导包

# 项目内部导包
from storage import init_db, cleanup_db


async def main():
    """主函数"""
    print("开始初始化日记洞察系统数据表...")
    
    try:
        # 初始化数据库表
        await init_db()
        print("✓ 数据表创建成功！")
        
        print("\n已创建的数据表：")
        print("  1. entries - 条目/记录表")
        print("  2. entry_images - 条目图片表")
        print("  3. tags - 标签表")
        print("  4. entry_tags - 条目标签关联表")
        print("  5. insight_cards - 洞察卡片表")
        print("  6. insight_card_configs - 洞察配置表")
        
    except Exception as e:
        print(f"✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 清理数据库连接
        await cleanup_db()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

