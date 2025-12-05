# Storage Layer - 日记洞察系统

## 概述

这是日记洞察系统的存储层实现，包含数据模型、Repository层和相关工具。

## 数据表设计

### 1. Entry（条目/记录表）
存储用户的日记条目，支持文本和语音输入。

**核心字段：**
- `id`: UUID主键
- `user_id`: 用户ID
- `content`: 文本内容（最多5000字）
- `emotion`: 情绪（positive/neutral/negative）
- `status`: 状态（sending/success/failed/violated）
- `is_visible`: 是否可见
- `created_at`: 创建时间
- `updated_at`: 更新时间

**扩展字段：**
- `events_json`: 1-3个核心事件的JSON数据
- `word_count`: 字数统计
- `audio_duration`: 语音时长
- `source_type`: 来源类型（text/voice）

### 2. EntryImage（条目图片表）
存储条目关联的图片。

**核心字段：**
- `id`: UUID主键
- `entry_id`: 关联的条目ID（外键）
- `image_url`: 图片URL
- `upload_status`: 上传状态（pending/uploading/success/failed）
- `is_live_photo`: 是否为Live Photo
- `sort_order`: 排序顺序

### 3. Tag（标签表）
存储系统标签和用户自定义标签。

**核心字段：**
- `id`: UUID主键
- `name`: 标签名称
- `tag_type`: 类型（system/custom）
- `user_id`: 用户ID（自定义标签需要）
- `is_enabled`: 是否启用
- `color`: 标签颜色（UI展示用）

### 4. EntryTag（条目标签关联表）
多对多关系表，关联条目和标签。

**核心字段：**
- `id`: UUID主键
- `entry_id`: 条目ID（外键）
- `tag_id`: 标签ID（外键）
- 唯一约束：(entry_id, tag_id)

### 5. InsightCard（洞察卡片表）
存储AI生成的洞察卡片。

**核心字段：**
- `id`: UUID主键
- `user_id`: 用户ID
- `card_type`: 卡片类型（daily_affirmation/weekly_emotion_map/weekly_gratitude_list/custom）
- `content_json`: 卡片内容（JSON格式）
- `data_start_time`: 数据源开始时间
- `data_end_time`: 数据源结束时间
- `is_viewed`: 是否已查看
- `is_hidden`: 是否已隐藏
- `generated_at`: 生成时间

### 6. InsightCardConfig（洞察配置表）
用户自定义洞察配置（付费功能）。

**核心字段：**
- `id`: UUID主键
- `user_id`: 用户ID
- `name`: 洞察名称
- `time_range`: 时间范围（daily/weekly/monthly）
- `prompt`: 洞察提示词
- `sort_order`: 排序顺序
- `is_enabled`: 是否启用

## Repository使用示例

### 1. EntryRepository

```python
from storage import get_session
from storage.repositories import EntryRepository
from datetime import datetime, timedelta

async for session in get_session():
    repo = EntryRepository(session)
    
    # 创建记录
    entry = await repo.create(
        user_id="user_123",
        content="今天天气很好",
        emotion="positive",
        status="success",
        word_count=6
    )
    
    # 查询用户的所有记录
    entries = await repo.get_by_user_id("user_123", limit=10)
    
    # 按时间范围查询
    start_time = datetime.utcnow() - timedelta(days=7)
    end_time = datetime.utcnow()
    week_entries = await repo.get_by_date_range(
        "user_123", 
        start_time, 
        end_time
    )
    
    # 按情绪查询
    positive_entries = await repo.get_by_emotion("user_123", "positive")
    
    # 统计
    count = await repo.count_by_user_and_date_range(
        "user_123",
        start_time,
        end_time
    )
```

### 2. TagRepository

```python
from storage.repositories import TagRepository

async for session in get_session():
    repo = TagRepository(session)
    
    # 创建系统标签
    tag = await repo.create(
        name="工作",
        tag_type="system",
        color="#4A90E2"
    )
    
    # 创建用户自定义标签
    custom_tag = await repo.create(
        name="我的项目",
        tag_type="custom",
        user_id="user_123",
        color="#FF0000"
    )
    
    # 获取用户所有可用标签（系统+自定义）
    all_tags = await repo.get_all_available_tags("user_123")
    
    # 按名称查询
    work_tag = await repo.get_by_name("工作")
```

### 3. EntryTagRepository

```python
from storage.repositories import EntryTagRepository

async for session in get_session():
    repo = EntryTagRepository(session)
    
    # 为条目添加标签
    entry_tag = await repo.add_tag_to_entry(entry_id, tag_id)
    
    # 获取条目的所有标签
    tags = await repo.get_tags_by_entry_id(entry_id)
    
    # 替换条目的标签
    new_tags = await repo.replace_entry_tags(
        entry_id,
        [tag_id1, tag_id2, tag_id3]
    )
    
    # 移除标签
    await repo.remove_tag_from_entry(entry_id, tag_id)
```

### 4. InsightCardRepository

```python
from storage.repositories import InsightCardRepository
from datetime import datetime, timedelta

async for session in get_session():
    repo = InsightCardRepository(session)
    
    # 创建洞察卡片
    now = datetime.utcnow()
    card = await repo.create(
        user_id="user_123",
        card_type="daily_affirmation",
        content_json={
            "message": "今天也要加油！",
            "mood": "positive"
        },
        data_start_time=now - timedelta(days=1),
        data_end_time=now
    )
    
    # 获取用户的所有卡片（不包括隐藏的）
    cards = await repo.get_by_user_id("user_123", is_hidden=False)
    
    # 按类型查询
    daily_cards = await repo.get_by_card_type("user_123", "daily_affirmation")
    
    # 获取最新的卡片
    latest = await repo.get_latest_by_type("user_123", "weekly_emotion_map")
    
    # 标记为已查看
    await repo.mark_as_viewed(card_id)
    
    # 增加分享次数
    await repo.increment_share_count(card_id)
```

### 5. InsightCardConfigRepository

```python
from storage.repositories import InsightCardConfigRepository

async for session in get_session():
    repo = InsightCardConfigRepository(session)
    
    # 创建配置
    config = await repo.create(
        user_id="user_123",
        name="每周工作总结",
        time_range="weekly",
        prompt="分析我本周的工作情况",
        sort_order=1
    )
    
    # 获取用户的所有配置
    configs = await repo.get_by_user_id("user_123")
    
    # 获取启用的配置
    enabled_configs = await repo.get_enabled_configs("user_123")
    
    # 切换启用状态
    await repo.toggle_enabled(config_id)
    
    # 批量更新排序
    await repo.update_sort_orders({
        config_id1: 0,
        config_id2: 1,
        config_id3: 2
    })
```

## 初始化脚本

### 1. 初始化数据表

```bash
cd /Users/tyc/Documents/privete/guanwo/base-server
python3 scripts/init_journal_tables.py
```

### 2. 初始化系统默认标签

```bash
python3 scripts/init_default_tags.py
```

这会创建3个系统默认标签：
- 学习工作
- 社交
- 健康

### 3. 运行测试

```bash
python3 scripts/test_journal_models.py
```

## 索引设计

为了优化查询性能，已创建以下索引：

1. **Entry表：**
   - `user_id` 单列索引
   - `created_at` 单列索引
   - `(user_id, created_at)` 复合索引

2. **EntryTag表：**
   - `(entry_id, tag_id)` 唯一索引

3. **InsightCard表：**
   - `user_id` 单列索引
   - `generated_at` 单列索引
   - `(user_id, is_hidden)` 复合索引

## 外键约束

- EntryImage.entry_id → Entry.id (ON DELETE CASCADE)
- EntryTag.entry_id → Entry.id (ON DELETE CASCADE)
- EntryTag.tag_id → Tag.id (ON DELETE CASCADE)
- InsightCard.config_id → InsightCardConfig.id (ON DELETE SET NULL)

## 注意事项

1. **UUID主键：** 所有表都使用UUID字符串作为主键，自动生成。

2. **时间字段：** 统一使用UTC时间。

3. **JSON字段：** `events_json` 和 `content_json` 使用SQLAlchemy的JSON类型存储结构化数据。

4. **级联删除：** 删除Entry时会自动删除关联的EntryImage和EntryTag。

5. **事务管理：** 使用 `get_session()` 作为依赖注入时，会自动管理事务（commit/rollback）。

## 开发规范

遵循项目的导包规范：

1. 标准库导包
2. 第三方库导包
3. 项目内部导包

每组之间用空行分隔，并添加对应的中文注释。

