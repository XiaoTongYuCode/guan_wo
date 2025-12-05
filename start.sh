#!/bin/bash

# Server 启动脚本

echo "正在启动Server..."

# 启动服务
echo "启动FastAPI服务..."
echo "服务将在 http://localhost:8000 上运行"
echo "API文档: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务"
echo ""

python main.py 