@echo off
chcp 65001 >nul
title 养基助手

echo.
echo ╔══════════════════════════════════╗
echo ║        📈 养基助手 v1.0          ║
echo ║   个人基金持仓管理与智能分析       ║
echo ╚══════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查 Python
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X 未找到 Python，请先安装 Python 3.11+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 安装 Python 依赖
echo 检查 Python 依赖...
py -3 -m pip install -r backend\requirements.txt -q 2>nul

:: 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Node.js，请先安装 Node.js
    echo    下载地址: https://nodejs.org/
    pause
    exit /b 1
)

:: 安装前端依赖 & 构建
echo 📦 检查前端依赖...
cd frontend
if not exist "node_modules" (
    echo 📥 正在安装前端依赖（仅首次需要）...
    call npm install --silent
)
echo 🔨 构建前端...
call npm run build --silent
cd ..

:: 启动后端服务
echo.
echo 🚀 启动服务中...
echo ┌────────────────────────────────────────┐
echo │  手机访问: 同一WiFi下浏览器打开          │
echo │  http://你的电脑IP:8765                 │
echo │                                        │
echo │  电脑访问: http://127.0.0.1:8765       │
echo │                                        │
echo │  按 Ctrl+C 停止服务                     │
echo └────────────────────────────────────────┘
echo.

start "" http://127.0.0.1:8765
py -3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8765

pause
