# TYC Universal Web Server

TYC (天眼查) Universal Web Server 是一个基于 FastAPI 构建的现代化 Web 服务，提供智能聊天服务和企业数据查询功能。

## 🚀 功能特性

- **智能聊天服务**: 支持流式对话和会话历史管理
- **多环境支持**: 开发、预发、生产环境配置
- **高性能**: 基于 FastAPI 异步框架，支持高并发请求
- **数据持久化**: MySQL 数据库存储 + Redis 缓存
- **用户认证**: 天眼查用户身份验证
- **API 文档**: 自动生成的 OpenAPI 文档
- **健康检查**: 服务状态监控接口

## 🛠 技术栈

- **后端框架**: FastAPI
- **异步运行时**: Uvicorn
- **数据库**: MySQL (SQLAlchemy ORM)
- **缓存**: Redis
- **认证**: 天眼查用户验证系统
- **配置管理**: Pydantic Settings
- **日志**: Python Logging

## 📁 项目结构

```
tyc-universal-server/
├── main.py                 # 应用程序入口
├── config.py              # 应用配置
├── models.py              # 数据模型
├── redis_client.py        # Redis 客户端
├── requirements.txt       # 依赖列表
├── start.sh              # 启动脚本
├── routers/              # API 路由
│   ├── basic.py          # 基础功能路由
│   ├── chat.py           # 聊天服务路由
│   ├── services/         # 业务服务层
│   └── utils/            # 路由工具类
├── storage/              # 数据存储层
│   ├── database.py       # 数据库配置
│   ├── models/           # 数据库模型
│   └── repositories/     # 数据访问层
└── utils/                # 通用工具
    └── auth.py           # 认证工具
```

## 🔧 安装与部署

### 环境要求

- Python 3.8+
- MySQL 5.7+
- Redis 6.0+

### 快速启动

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd tyc-universal-server
   ```

2. **使用启动脚本（推荐）**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

3. **手动启动**
   ```bash
   # 创建虚拟环境
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或者 venv\Scripts\activate  # Windows
   
   # 安装依赖
   pip install -r requirements.txt
   
   # 启动服务
   python main.py
   ```

### 环境配置

通过环境变量或 `.env` 文件配置：

```bash
# 环境设置
POD_ENV=test  # test/yufa/online

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 数据库和Redis连接会根据POD_ENV自动选择
```

## 📖 API 文档

服务启动后，可通过以下地址访问 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 主要 API 端点

#### 基础功能
- `GET /`: 服务欢迎信息
- `GET /health`: 健康检查

#### 聊天服务
- `POST /chat/stream`: 流式聊天服务
- `GET /chat/sessions/{user_id}`: 获取用户会话列表
- `GET /chat/history/{session_id}`: 获取会话历史
- `DELETE /chat/sessions/{session_id}`: 删除会话

## 🔐 认证方式

API 使用天眼查用户认证系统，需要在请求头中包含认证信息：

```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "查询企业信息",
    "mode": "fast",
    "session_id": null
  }'
```

## 📊 数据模型

### UserInfo (用户信息)
```python
{
  "mobile": "13800138000",
  "name": "张三",
  "user_id": "123456"
}
```

### SearchParams (搜索参数)
```python
{
  "query": "搜索内容",
  "mode": "fast",  # fast | deep
  "session_id": "session_123"
}
```

### SessionHistory (会话历史)
```python
{
  "user_id": "123456",
  "session_id": "session_123",
  "messages": [...],
  "message_count": 10,
  "timestamp": 1640995200
}
```

## 🌍 多环境配置

项目支持多环境部署，通过 `POD_ENV` 环境变量控制：

- **test**: 开发环境（默认）
- **yufa**: 预发环境  
- **online**: 生产环境

不同环境使用不同的数据库和 Redis 连接配置。

## 📝 日志

应用使用 Python 标准 logging 模块，支持不同级别的日志输出：

```bash
# 设置日志级别
export LOG_LEVEL=info  # debug/info/warning/error
```

## 🔍 监控与健康检查

- **健康检查端点**: `GET /health`
- **服务状态**: 返回服务运行状态和各组件检查结果
- **监控指标**: API 响应时间、内存使用、磁盘状态等

## 🤝 开发指南

### 代码规范

项目遵循以下 Python 代码规范：

1. **导包顺序**: 标准库 → 第三方库 → 项目内部
2. **类型提示**: 使用 typing 模块进行类型标注
3. **文档字符串**: 函数和类需要包含文档说明
4. **异常处理**: 合理使用异常处理和日志记录

### 新功能开发

1. 在 `routers/` 目录下创建新的路由文件
2. 在 `services/` 目录下实现业务逻辑
3. 在 `models.py` 中定义数据模型
4. 更新 `main.py` 注册新路由

## 🐛 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证连接配置和权限

2. **Redis 连接失败**
   - 确认 Redis 服务状态
   - 检查网络连接和密码

3. **认证失败**
   - 验证认证 token 的有效性
   - 检查用户权限设置

### 调试模式

```bash
# 启用调试模式
export POD_ENV=test
export LOG_LEVEL=debug
python main.py
```

## 📄 许可证

[请根据实际情况添加许可证信息]

## 👥 贡献

[请根据实际情况添加贡献指南]

---

**联系方式**: [请添加联系信息]
**项目维护**: TYC 开发团队
