"""应用配置"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库路径
DATABASE_PATH = BASE_DIR / "data" / "fund_manager.db"

# 前端静态文件路径（构建后）
STATIC_DIR = BASE_DIR / "frontend" / "dist"

# 服务配置
HOST = "0.0.0.0"
PORT = 8765

# 数据更新配置
MARKET_REFRESH_SECONDS = 30   # 指数/板块行情刷新间隔
NAV_REFRESH_HOUR = 17         # 净值更新检查时间（下午5点）
CACHE_TTL_SECONDS = {
    "nav": 3600,              # 净值缓存1小时
    "market": 30,             # 行情缓存30秒
    "fund_list": 86400,       # 基金列表缓存24小时
    "fund_detail": 86400,     # 基金详情缓存24小时
}

# 频率限制
API_RATE_LIMIT = 2  # 每秒最多2次请求（东方财富限制）
