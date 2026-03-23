#!/bin/bash

set -e

echo "=== IT运维平台启动脚本 ==="
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 读取 .env（如果存在）
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# 默认走 PostgreSQL（可被 .env 中 DATABASE_URL 覆盖）
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db}"

# 检查 Python
echo "检查 Python 版本..."
python --version

# 启动后端
echo ""
echo "启动后端服务..."
cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装后端依赖..."
pip install -q -r requirements.txt

# 启动后端
echo ""
echo "启动后端服务 (端口: 5000)..."
echo "数据库: ${DATABASE_URL}"
echo "初始用户: admin / admin"
echo ""
python run.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

cd ..

# 启动前端
echo ""
echo "启动前端服务..."
cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

echo "启动前端开发服务器 (端口: 3000)..."
echo ""
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== 服务启动成功 ==="
echo "后端地址: http://localhost:5000"
echo "前端地址: http://localhost:3000"
echo "登录账号: admin"
echo "登录密码: admin"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户按 Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
