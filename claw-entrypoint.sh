#!/bin/sh
# ClawCloud 轻量级启动脚本
# 特点：简化架构，降低资源占用

# 创建必要的目录
mkdir -p /app/data /app/reports

echo "========================================"
echo "AI基金分析助手 - ClawCloud"
echo "========================================"

# 初始化数据库
echo "正在初始化数据库..."
python -c "
from app.data.database import init_db
init_db()
print('数据库初始化完成')
"

# 启动后端服务（后台，本地访问）
echo "正在启动 FastAPI 服务..."
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --workers 1 &

# 等待后端启动
sleep 2

# 启动前端服务（主进程，对外暴露）
echo "正在启动 Streamlit 服务..."
exec streamlit run app/ui/main.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
