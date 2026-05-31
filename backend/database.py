"""数据库模型和连接管理"""

import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH

# 确保数据目录存在
os.makedirs(DATABASE_PATH.parent, exist_ok=True)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户持仓表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            fund_name TEXT NOT NULL DEFAULT '',
            fund_type TEXT DEFAULT '',
            buy_amount REAL NOT NULL DEFAULT 0,      -- 投入金额(元)
            buy_shares REAL NOT NULL DEFAULT 0,       -- 持有份额
            buy_nav REAL NOT NULL DEFAULT 0,          -- 买入时净值
            buy_date TEXT NOT NULL DEFAULT '',        -- 买入日期
            platform TEXT DEFAULT '手动录入',          -- 来源平台
            notes TEXT DEFAULT '',                     -- 备注
            auto_invest TEXT DEFAULT '',              -- 定投: 'weekly,500' or 'monthly,1000'
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 交易记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holding_id INTEGER NOT NULL,
            fund_code TEXT NOT NULL,
            type TEXT NOT NULL,                       -- 'buy', 'sell', 'auto'
            amount REAL NOT NULL DEFAULT 0,            -- 交易金额
            shares REAL NOT NULL DEFAULT 0,            -- 交易份额
            nav REAL NOT NULL DEFAULT 0,              -- 交易净值
            date TEXT NOT NULL DEFAULT '',             -- 交易日期
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (holding_id) REFERENCES holdings(id)
        )
    """)

    # 基金净值缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nav_cache (
            fund_code TEXT NOT NULL,
            date TEXT NOT NULL,
            unit_nav REAL NOT NULL DEFAULT 0,         -- 单位净值
            acc_nav REAL NOT NULL DEFAULT 0,          -- 累计净值
            daily_return REAL NOT NULL DEFAULT 0,     -- 日增长率(%)
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (fund_code, date)
        )
    """)

    # 基金信息缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fund_info (
            fund_code TEXT PRIMARY KEY,
            fund_name TEXT NOT NULL,
            fund_type TEXT DEFAULT '',
            company TEXT DEFAULT '',
            manager TEXT DEFAULT '',
            establish_date TEXT DEFAULT '',
            scale REAL DEFAULT 0,                     -- 基金规模(亿)
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 指数行情缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_cache (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            change_pct REAL DEFAULT 0,
            change_amt REAL DEFAULT 0,
            volume REAL DEFAULT 0,
            high REAL DEFAULT 0,
            low REAL DEFAULT 0,
            open REAL DEFAULT 0,
            prev_close REAL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 板块行情缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sector_cache (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            change_pct REAL DEFAULT 0,
            main_inflow REAL DEFAULT 0,              -- 主力净流入(亿)
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 每日收益记录表（用于收益日历和趋势图）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_profit (
            date TEXT PRIMARY KEY,
            total_value REAL NOT NULL DEFAULT 0,      -- 当日总市值
            total_cost REAL NOT NULL DEFAULT 0,       -- 总成本
            profit REAL NOT NULL DEFAULT 0,           -- 当日盈亏
            profit_pct REAL NOT NULL DEFAULT 0,       -- 当日收益率(%)
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()


# 初始化
init_db()
