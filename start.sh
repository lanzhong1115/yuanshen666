#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════╗"
echo "║        📈 养基助手 v1.0          ║"
echo "║   个人基金持仓管理与智能分析       ║"
echo "╚══════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.11+"
    exit 1
fi

# 安装 Python 依赖
echo "📦 检查 Python 依赖..."
pip3 install -r backend/requirements.txt -q 2>/dev/null || pip install -r backend/requirements.txt -q 2>/dev/null

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 安装前端依赖 & 构建
echo "📦 检查前端依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📥 正在安装前端依赖（仅首次需要）..."
    npm install --silent
fi
echo "🔨 构建前端..."
npm run build --silent
cd ..

# 获取本机 IP
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo ""
echo "🚀 启动服务中..."
echo "────────────────────────────────────────"
echo "  手机访问: http://$IP:8765"
echo "  电脑访问: http://127.0.0.1:8765"
echo "  按 Ctrl+C 停止服务"
echo "────────────────────────────────────────"
echo ""

# 自动打开浏览器
sleep 1 && open http://127.0.0.1:8765 2>/dev/null &

python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8765
