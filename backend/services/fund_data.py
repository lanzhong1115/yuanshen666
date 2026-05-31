"""基金数据服务 — 通过 AKShare 和东方财富 API 拉取数据"""

import httpx
import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from database import get_db
from config import CACHE_TTL_SECONDS, API_RATE_LIMIT

# 简单的频率限制器
_last_request_time = 0

# 基金列表全局缓存（避免每次搜索都下载~1MB文件）
_fund_list_cache = None
_fund_list_cache_time = 0


def rate_limit():
    """简单的请求频率限制"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 1.0 / API_RATE_LIMIT:
        time.sleep(1.0 / API_RATE_LIMIT - elapsed)
    _last_request_time = time.time()


def _load_fund_list() -> list:
    """加载完整的基金列表（带缓存，24小时有效）"""
    global _fund_list_cache, _fund_list_cache_time
    now = time.time()
    if _fund_list_cache is not None and (now - _fund_list_cache_time) < 86400:
        return _fund_list_cache

    try:
        url = "http://fund.eastmoney.com/js/fundcode_search.js"
        resp = httpx.get(url, timeout=15)
        resp.encoding = 'utf-8'
        text = resp.text
        match = re.search(r'var\s+r\s*=\s*(\[\[.*?\]\]);', text, re.DOTALL)
        if match:
            _fund_list_cache = json.loads(match.group(1))
            _fund_list_cache_time = now
            return _fund_list_cache
    except Exception as e:
        print(f"[fund_data] 加载基金列表失败: {e}")

    return _fund_list_cache or []


def search_funds(query: str) -> list:
    """搜索基金（从东方财富基金列表）"""
    fund_list = _load_fund_list()
    if not fund_list:
        return []

    results = []
    query_lower = query.lower()
    for item in fund_list:
        code = item[0]
        name = item[2]
        ftype = item[3] if len(item) > 3 else ""
        if query_lower in code or query_lower in name.lower():
            results.append({
                "fund_code": code,
                "fund_name": name,
                "fund_type": ftype,
            })
    return results[:30]


def get_fund_info(fund_code: str) -> dict:
    """获取基金基本信息 — 名称从搜索缓存取，净值从东方财富取"""
    # 名称和类型从全局搜索缓存获取（最可靠）
    fund_name = ""
    fund_type = ""
    fund_list = _load_fund_list()
    for item in fund_list:
        if item[0] == fund_code:
            fund_name = item[2]
            fund_type = item[3] if len(item) > 3 else ""
            break

    # 净值从东方财富API获取
    latest_nav = 0
    latest_date = ""
    try:
        url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        resp = httpx.get(url, timeout=10)
        resp.encoding = 'utf-8'
        text = resp.text

        nav_data = _extract_json_array(text, 'Data_netWorthTrend')
        if nav_data and len(nav_data) > 0:
            latest_nav = nav_data[-1]["y"]
            latest_date_ms = nav_data[-1]["x"]
            latest_date = datetime.fromtimestamp(latest_date_ms / 1000).strftime("%Y-%m-%d") if latest_date_ms else ""
    except Exception as e:
        print(f"[fund_data] 获取净值失败 {fund_code}: {e}")

    return {"fund_code": fund_code, "fund_name": fund_name, "fund_type": fund_type, "latest_nav": latest_nav, "latest_date": latest_date}


def _extract_json_array(text: str, var_name: str) -> list:
    """从JS文本中提取JSON数组（括号计数法，更可靠）"""
    # 找到变量赋值位置
    pattern = var_name + r'\s*=\s*'
    match = re.search(pattern, text)
    if not match:
        return []

    start_pos = match.end()
    # 跳过空白找到 [
    while start_pos < len(text) and text[start_pos] in ' \t\n\r':
        start_pos += 1
    if start_pos >= len(text) or text[start_pos] != '[':
        return []

    # 括号计数找到匹配的 ]
    bracket_count = 0
    in_string = False
    escape = False
    for i in range(start_pos, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '[':
            bracket_count += 1
        elif c == ']':
            bracket_count -= 1
            if bracket_count == 0:
                json_str = text[start_pos:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # 尝试修复NaN/Infinity等JS专有值
                    json_str = json_str.replace('NaN', 'null').replace('Infinity', 'null').replace('-Infinity', 'null')
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        return []
        elif bracket_count == 0:
            break
    return []


def get_fund_nav_history(fund_code: str, days: int = 90) -> list:
    """获取基金历史净值（优先缓存）"""
    # 先查缓存
    conn = get_db()
    cursor = conn.cursor()
    cutoff_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT * FROM nav_cache WHERE fund_code=? AND date >= ? ORDER BY date ASC",
        (fund_code, cutoff_str)
    )
    cached = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if cached and len(cached) >= 3:
        latest_date = datetime.strptime(cached[-1]["date"], "%Y-%m-%d")
        earliest_cached = cached[0]["date"]
        hours_age = (datetime.now() - latest_date).total_seconds() / 3600
        # 缓存必须覆盖请求的时间范围 + 3天内有效
        if hours_age < 72 and earliest_cached <= cutoff_str:
            return [{"date": r["date"], "nav": r["unit_nav"], "acc_nav": r["acc_nav"], "daily_return": r["daily_return"]} for r in cached]

    # 缓存失效，从API获取
    rate_limit()
    try:
        url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        resp = httpx.get(url, timeout=10)
        resp.encoding = 'utf-8'
        text = resp.text

        nav_data = _extract_json_array(text, 'Data_netWorthTrend')
        if not nav_data:
            # 尝试不区分大小写
            nav_data = _extract_json_array(text, 'Data_netWorthTrend')
            if not nav_data:
                return []

        # 获取累计净值 (注意: Data_ACWorthTrend 格式是 [[ts, nav], ...] 而非 [{x:ts, y:nav}, ...])
        acc_data = _extract_json_array(text, 'Data_ACWorthTrend')

        acc_dict = {}
        if acc_data:
            for item in acc_data:
                if isinstance(item, list) and len(item) >= 2:
                    acc_dict[item[0]] = item[1]  # [[ts, nav], ...]
                elif isinstance(item, dict):
                    acc_dict[item["x"]] = item["y"]  # [{"x": ts, "y": nav}, ...]

        cutoff_date = (datetime.now() - timedelta(days=days)).timestamp() * 1000
        result = []
        for item in nav_data:
            if item["x"] >= cutoff_date:
                date_str = datetime.fromtimestamp(item["x"] / 1000).strftime("%Y-%m-%d")
                result.append({
                    "date": date_str,
                    "nav": round(item["y"], 4),
                    "acc_nav": round(acc_dict.get(item["x"], 0), 4),
                })

        # 计算每日收益率
        for i in range(1, len(result)):
            if result[i-1]["nav"] > 0:
                result[i]["daily_return"] = round(
                    (result[i]["nav"] - result[i-1]["nav"]) / result[i-1]["nav"] * 100, 2
                )
            else:
                result[i]["daily_return"] = 0
        if result:
            result[0]["daily_return"] = 0

        # 存入缓存
        conn = get_db()
        cursor = conn.cursor()
        for r in result:
            cursor.execute("INSERT OR REPLACE INTO nav_cache(fund_code,date,unit_nav,acc_nav,daily_return) VALUES(?,?,?,?,?)",
                [fund_code, r["date"], r["nav"], r["acc_nav"], r.get("daily_return", 0)])
        conn.commit()
        conn.close()

        return result
    except Exception as e:
        print(f"[fund_data] 获取净值历史失败 {fund_code}: {e}")
        return []


def get_fund_latest_nav(fund_code: str) -> dict:
    """获取基金最新净值（优先缓存，减少重复API调用）"""
    # 1. 先查缓存
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM nav_cache WHERE fund_code = ? ORDER BY date DESC LIMIT 1",
        (fund_code,)
    )
    row = cursor.fetchone()
    conn.close()

    now = datetime.now()
    cache_valid = False
    if row:
        cache_date = datetime.strptime(row["date"], "%Y-%m-%d")
        hours_since = (now - cache_date).total_seconds() / 3600
        # 交易时段(9-17点)缓存30分钟有效，非交易时段缓存到下一次开盘
        is_trading_hour = 9 <= now.hour <= 17 and now.weekday() < 5
        max_age = 0.5 if is_trading_hour else 6
        cache_valid = hours_since < max_age

    if cache_valid and row["unit_nav"] > 0:
        return {
            "fund_code": fund_code,
            "nav": row["unit_nav"],
            "acc_nav": row["acc_nav"],
            "date": row["date"],
            "daily_return": row["daily_return"],
            "from_cache": True,
        }

    # 2. 缓存过期或不存在，从API获取
    nav_history = get_fund_nav_history(fund_code, days=5)
    if nav_history:
        latest = nav_history[-1]
        prev = nav_history[-2] if len(nav_history) > 1 else latest

        # 更新缓存
        conn = get_db()
        cursor = conn.cursor()
        for n in nav_history[-5:]:
            cursor.execute("""
                INSERT OR REPLACE INTO nav_cache (fund_code, date, unit_nav, acc_nav, daily_return)
                VALUES (?, ?, ?, ?, ?)
            """, (fund_code, n["date"], n["nav"], n["acc_nav"], n.get("daily_return", 0)))
        conn.commit()
        conn.close()

        return {
            "fund_code": fund_code,
            "nav": latest["nav"],
            "acc_nav": latest["acc_nav"],
            "date": latest["date"],
            "daily_return": latest.get("daily_return", 0),
            "prev_nav": prev["nav"],
            "from_cache": False,
        }

    # 3. API失败但缓存存在（过期也先用着）
    if row and row["unit_nav"] > 0:
        return {
            "fund_code": fund_code,
            "nav": row["unit_nav"],
            "acc_nav": row["acc_nav"],
            "date": row["date"],
            "daily_return": row["daily_return"],
            "from_cache": True,
        }

    return {"fund_code": fund_code, "nav": 0, "acc_nav": 0, "date": "", "daily_return": 0}


def get_fund_holdings(fund_code: str, year: str = "2025") -> list:
    """获取基金前十大持仓"""
    rate_limit()
    try:
        import akshare as ak
        df = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
        if df is not None and not df.empty:
            results = []
            for _, row in df.iterrows():
                results.append({
                    "stock_code": str(row.get("股票代码", "")),
                    "stock_name": str(row.get("股票名称", "")),
                    "ratio": float(row.get("占净值比例", 0)),
                    "shares": float(row.get("持股数", 0)) if "持股数" in row else 0,
                    "market_value": float(row.get("持仓市值", 0)) if "持仓市值" in row else 0,
                })
            return results
    except Exception as e:
        print(f"[fund_data] 获取持仓失败 {fund_code}: {e}")

    return []


def get_fund_sector_allocation(fund_code: str) -> list:
    """获取基金行业配置"""
    rate_limit()
    try:
        import akshare as ak
        df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date="2025")
        if df is not None and not df.empty:
            results = []
            for _, row in df.iterrows():
                results.append({
                    "industry": str(row.get("行业", "")),
                    "ratio": float(row.get("占净值比例", 0)),
                })
            return results
    except Exception as e:
        print(f"[fund_data] 获取行业配置失败 {fund_code}: {e}")

    return []
