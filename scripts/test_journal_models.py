"""
测试日记洞察系统的模型和Repository
"""
# 标准库导包
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 项目内部导包
from storage import get_session, cleanup_db
from storage.repositories import (
    EntryRepository,
    EntryImageRepository,
    TagRepository,
    EntryTagRepository,
    InsightCardRepository,
    InsightCardConfigRepository
)


async def test_entry_operations():
    """测试Entry的CRUD操作"""
    print("\n=== 测试Entry操作 ===")
    
    async for session in get_session():
        repo = EntryRepository(session)
        
        # 创建
        entry = await repo.create(
            user_id="test_user_001",
            content="今天天气很好，心情不错！",
            emotion="positive",
            status="success",
            word_count=12,
            source_type="text"
        )
        print(f"✓ 创建Entry: {entry.id}")
        
        # 查询
        found_entry = await repo.get_by_id(entry.id)
        assert found_entry is not None
        print(f"✓ 查询Entry: {found_entry.content[:20]}...")
        
        # 更新
        updated_entry = await repo.update_by_id(entry.id, emotion="neutral")
        assert updated_entry.emotion == "neutral"
        print(f"✓ 更新Entry: emotion={updated_entry.emotion}")
        
        # 按用户ID查询
        user_entries = await repo.get_by_user_id("test_user_001", limit=10)
        print(f"✓ 查询用户记录: 找到{len(user_entries)}条")
        
        # 删除
        deleted = await repo.delete_by_id(entry.id)
        assert deleted is True
        print(f"✓ 删除Entry: {entry.id}")
        
        return True


async def test_tag_operations():
    """测试Tag的CRUD操作"""
    print("\n=== 测试Tag操作 ===")
    
    async for session in get_session():
        repo = TagRepository(session)
        
        # 创建系统标签
        system_tag = await repo.create(
            name="测试标签",
            tag_type="system",
            color="#FF0000",
            icon="test"
        )
        print(f"✓ 创建系统标签: {system_tag.name}")
        
        # 创建自定义标签
        custom_tag = await repo.create(
            name="我的自定义标签",
            tag_type="custom",
            user_id="test_user_001",
            color="#00FF00"
        )
        print(f"✓ 创建自定义标签: {custom_tag.name}")
        
        # 查询系统标签
        system_tags = await repo.get_system_tags()
        print(f"✓ 查询系统标签: 找到{len(system_tags)}个")
        
        # 查询用户自定义标签
        custom_tags = await repo.get_user_custom_tags("test_user_001")
        print(f"✓ 查询用户自定义标签: 找到{len(custom_tags)}个")
        
        # 查询所有可用标签
        all_tags = await repo.get_all_available_tags("test_user_001")
        print(f"✓ 查询所有可用标签: 找到{len(all_tags)}个")
        
        # 清理
        await repo.delete_by_id(system_tag.id)
        await repo.delete_by_id(custom_tag.id)
        print(f"✓ 清理测试标签")
        
        return True


async def test_entry_tag_operations():
    """测试EntryTag关联操作"""
    print("\n=== 测试EntryTag关联操作 ===")
    
    async for session in get_session():
        entry_repo = EntryRepository(session)
        tag_repo = TagRepository(session)
        entry_tag_repo = EntryTagRepository(session)
        
        # 创建测试数据
        entry = await entry_repo.create(
            user_id="test_user_001",
            content="测试内容",
            status="success"
        )
        tag1 = await tag_repo.create(name="标签1", tag_type="system")
        tag2 = await tag_repo.create(name="标签2", tag_type="system")
        
        print(f"✓ 创建测试数据: Entry={entry.id}, Tag1={tag1.id}, Tag2={tag2.id}")
        
        # 添加标签
        entry_tag1 = await entry_tag_repo.add_tag_to_entry(entry.id, tag1.id)
        entry_tag2 = await entry_tag_repo.add_tag_to_entry(entry.id, tag2.id)
        print(f"✓ 为Entry添加2个标签")
        
        # 查询Entry的所有标签
        tags = await entry_tag_repo.get_tags_by_entry_id(entry.id)
        print(f"✓ 查询Entry的标签: 找到{len(tags)}个")
        assert len(tags) == 2
        
        # 移除一个标签
        removed = await entry_tag_repo.remove_tag_from_entry(entry.id, tag1.id)
        assert removed is True
        print(f"✓ 移除一个标签")
        
        # 再次查询
        tags = await entry_tag_repo.get_tags_by_entry_id(entry.id)
        assert len(tags) == 1
        print(f"✓ 验证标签已移除: 剩余{len(tags)}个")
        
        # 清理
        await entry_repo.delete_by_id(entry.id)
        await tag_repo.delete_by_id(tag1.id)
        await tag_repo.delete_by_id(tag2.id)
        print(f"✓ 清理测试数据")
        
        return True


async def test_entry_range_and_count():
    """测试时间范围查询与计数"""
    print("\n=== 测试时间范围查询与计数 ===")

    async for session in get_session():
        repo = EntryRepository(session)
        now = datetime.utcnow()
        start_time = now - timedelta(days=1)
        end_time = now + timedelta(days=1)

        entry1 = await repo.create(
            user_id="range_user_001",
            content="范围测试1",
            status="success",
            created_at=now - timedelta(hours=1)
        )
        entry2 = await repo.create(
            user_id="range_user_001",
            content="范围测试2",
            status="failed",
            created_at=now
        )

        entries = await repo.get_by_date_range(
            user_id="range_user_001",
            start_time=start_time,
            end_time=end_time,
            limit=10,
            offset=0
        )
        print(f"✓ 按范围查询到 {len(entries)} 条")

        count_all = await repo.count_by_user_and_date_range(
            user_id="range_user_001",
            start_time=start_time,
            end_time=end_time
        )
        print(f"✓ 总数统计: {count_all}")

        await repo.delete_by_id(entry1.id)
        await repo.delete_by_id(entry2.id)
        print("✓ 清理范围测试数据")

        return True


async def test_insight_card_operations():
    """测试InsightCard操作"""
    print("\n=== 测试InsightCard操作 ===")
    
    async for session in get_session():
        repo = InsightCardRepository(session)
        
        # 创建洞察卡片
        now = datetime.utcnow()
        card = await repo.create(
            user_id="test_user_001",
            card_type="daily_affirmation",
            content_json={"message": "今天也要加油哦！", "mood": "positive"},
            data_start_time=now - timedelta(days=1),
            data_end_time=now,
            is_viewed=False,
            is_hidden=False
        )
        print(f"✓ 创建洞察卡片: {card.id}")
        
        # 查询用户的卡片
        cards = await repo.get_by_user_id("test_user_001")
        print(f"✓ 查询用户卡片: 找到{len(cards)}个")
        
        # 按类型查询
        type_cards = await repo.get_by_card_type("test_user_001", "daily_affirmation")
        print(f"✓ 按类型查询: 找到{len(type_cards)}个")
        
        # 标记为已查看
        viewed_card = await repo.mark_as_viewed(card.id)
        assert viewed_card.is_viewed is True
        print(f"✓ 标记为已查看")
        
        # 增加分享次数
        shared_card = await repo.increment_share_count(card.id)
        assert shared_card.share_count == 1
        print(f"✓ 增加分享次数: {shared_card.share_count}")
        
        # 清理
        await repo.delete_by_id(card.id)
        print(f"✓ 清理测试数据")
        
        return True


async def test_insight_config_operations():
    """测试InsightCardConfig操作"""
    print("\n=== 测试InsightCardConfig操作 ===")
    
    async for session in get_session():
        repo = InsightCardConfigRepository(session)
        
        # 创建配置
        config = await repo.create(
            user_id="test_user_001",
            name="每周工作总结",
            time_range="weekly",
            prompt="帮我总结本周的工作情况",
            sort_order=1
        )
        print(f"✓ 创建配置: {config.name}")
        
        # 查询用户配置
        configs = await repo.get_by_user_id("test_user_001")
        print(f"✓ 查询用户配置: 找到{len(configs)}个")
        
        # 按时间范围查询
        weekly_configs = await repo.get_by_time_range("test_user_001", "weekly")
        print(f"✓ 按时间范围查询: 找到{len(weekly_configs)}个")
        
        # 切换启用状态
        toggled_config = await repo.toggle_enabled(config.id)
        assert toggled_config.is_enabled is False
        print(f"✓ 切换启用状态: {toggled_config.is_enabled}")
        
        # 清理
        await repo.delete_by_id(config.id)
        print(f"✓ 清理测试数据")
        
        return True


async def main():
    """主函数"""
    print("开始测试日记洞察系统...")
    
    try:
        # 运行所有测试
        await test_entry_operations()
        await test_tag_operations()
        await test_entry_tag_operations()
        await test_entry_range_and_count()
        await test_insight_card_operations()
        await test_insight_config_operations()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 清理数据库连接
        await cleanup_db()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

