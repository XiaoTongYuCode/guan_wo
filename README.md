# Guanwo Base Server

Guanwo Base Server 是一套基于 FastAPI 的个人情绪与洞察服务。它支持日记记录与分析、情绪趋势洞察、每日寄语生成，以及基础健康检查与跨域访问控制，后端对接 MySQL 与 Redis，并封装 LLM 客户端进行提示词驱动的内容生成。

## 功能
- 日记分析：解析用户日记，提取事件、情绪、标签
- 洞察卡片：生成每日寄语与情绪摘要
- 标签追踪与闪念（flash）：提供轻量记录与检索
- 健康检查与基础信息接口
- OpenAPI 文档（开发环境自动开启）

## 技术栈
- FastAPI + Uvicorn
- Pydantic Settings 配置管理
- MySQL + 异步数据库访问层
- Redis 缓存与会话
- LLM 客户端（多提供商配置，模板化提示词）
- Python logging

## 目录结构
```
base-server/
├── main.py                 # 应用入口与路由挂载
├── config.py               # 环境与服务配置
├── prompt.py               # 提示词模板管理
├── routers/                # 路由层
│   ├── basic.py            # 健康检查、根路由
│   ├── journal.py          # 日记相关接口
│   ├── insights.py         # 洞察相关接口
│   ├── tag_tracking.py     # 标签追踪接口
│   ├── flash.py            # 闪念记录接口
│   └── services/           # 业务逻辑封装
├── storage/                # 数据存储层
│   ├── database.py         # 数据库初始化与清理
│   ├── models/             # ORM 模型
│   └── repositories/       # 仓储模式实现
├── llm/                    # LLM 客户端与配置
├── requirements.txt        # 依赖列表
└── start.sh                # 可选启动脚本
```

## 快速开始
环境要求：Python 3.8+，MySQL 5.7+，Redis 6.0+

```bash
git clone <repo-url>
cd base-server
python3 -m venv venv
source venv/bin/activate   # Windows 请使用 venv\Scripts\activate
pip install -r requirements.txt

# 运行开发环境（默认开启 /docs）
python main.py
# 或：uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 环境变量
通过 `.env` 或系统环境变量配置（关键项）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| POD_ENV | 环境标识，test/yufa/online | test |
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 8000 |
| LOG_LEVEL | 日志级别 | info |
| DB_NAME | 数据库名称 | guanwo_db |
| DEV_DB_HOST / USER / PASSWORD | 开发库连接 | localhost:3306 / root / 12345678 |
| ONLINE_DB_HOST / USER / PASSWORD | 线上库连接 | localhost:3306 / root / 12345678 |
| REDIS_DEV_URL / REDIS_YUFA_URL / REDIS_ONLINE_URL | Redis 连接 | redis://localhost:6379/0 |
| DEFAULT_LLM_PROVIDER | 默认 LLM 提供商 | siliconflow |
| DEFAULT_LLM_MODEL_KEY | 默认模型键 | kimi-k2 |
| LLM_PROVIDERS | LLM 提供商配置（含 api_key/base_url/models） | config.py 中提供示例 |

提示：线上环境请覆盖默认的数据库、Redis 与 LLM api_key。

## 运行与调试
- 开发模式：`POD_ENV=test` 时自动开启 `/docs`、`/redoc`、`/openapi.json`
- 生产建议：使用 `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`
- 日志级别可通过 `LOG_LEVEL` 控制（debug/info/warning/error）

## API 说明
- 健康检查：`GET /health`
- 日记与洞察：`routers/journal.py`、`routers/insights.py`
- 标签追踪：`routers/tag_tracking.py`
- 闪念记录：`routers/flash.py`
- OpenAPI 文档：`/docs` 或 `/redoc`（仅非 online 环境）

## 开发约定
- 导入顺序：标准库 → 第三方库 → 项目内部（见项目规则）
- 业务逻辑放在 `routers/services`，数据访问通过 `storage/repositories`
- LLM 提示词集中在 `prompt.py`，采用占位符模板统一管理

## 常见问题
- **无法连接数据库/Redis**：确认服务已启动，检查连接串与账号权限
- **LLM 调用失败**：检查 `LLM_PROVIDERS` 配置与网络访问，替换为有效 api_key
- **文档未显示**：确认 `POD_ENV` 非 online，或手动设置 `DEBUG=true`
