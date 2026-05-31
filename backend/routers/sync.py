"""
聚合数据 API — 单次请求返回所有数据
核心优化: 每个基金代码只拉取一次净值历史，复用所有计算
"""
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter
from database import get_db
from services.fund_data import _extract_json_array
from services.market_data import get_index_quotes, get_sector_quotes
from services.advisor import diagnose_portfolio, recommend_allocation, generate_trade_signals, assess_risk
import httpx

router = APIRouter()
EXECUTOR = ThreadPoolExecutor(max_workers=4)

# 内存缓存：避免每次请求都查SQLite
_mem_cache = {"data": None, "time": 0, "ttl": 30}  # 30秒TTL

def _cached_sync():
    """内存缓存包装：30秒内重复请求直接返回缓存"""
    now = datetime.now().timestamp()
    if _mem_cache["data"] and (now - _mem_cache["time"]) < _mem_cache["ttl"]:
        return _mem_cache["data"]
    return None


def _get_nav_from_db(fund_code: str, days: int = 90) -> list:
    """仅从数据库缓存读取净值（不调用API）"""
    conn = get_db()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT * FROM nav_cache WHERE fund_code=? AND date >= ? ORDER BY date ASC",
        (fund_code, cutoff)
    )
    cached = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not cached or len(cached) < 3:
        return []

    latest = cached[-1]
    latest_date = datetime.strptime(latest["date"], "%Y-%m-%d")
    hours_age = (datetime.now() - latest_date).total_seconds() / 3600
    if hours_age > 72:  # 超过3天认为过期
        return []

    return [{"date": r["date"], "nav": r["unit_nav"], "acc_nav": r["acc_nav"], "daily_return": r["daily_return"]} for r in cached]


def _get_nav_history_cached(fund_code: str, days: int = 90) -> list:
    """带数据库缓存的净值历史获取（每个fund_code最多请求一次东方财富API）"""
    # 先查缓存
    conn = get_db()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT * FROM nav_cache WHERE fund_code=? AND date >= ? ORDER BY date ASC",
        (fund_code, cutoff)
    )
    cached = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # 缓存有效条件：有数据且最新数据在3个日历日内（跨周末）
    cache_fresh = False
    if cached:
        latest = cached[-1]
        latest_date = datetime.strptime(latest["date"], "%Y-%m-%d")
        hours_age = (datetime.now() - latest_date).total_seconds() / 3600
        cache_fresh = hours_age < 72 and len(cached) >= 3  # 3天内的缓存都有效

    if cache_fresh:
        # 转换格式
        return [{
            "date": r["date"],
            "nav": r["unit_nav"],
            "acc_nav": r["acc_nav"],
            "daily_return": r["daily_return"],
        } for r in cached]

    # 从东方财富API获取
    try:
        url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        resp = httpx.get(url, timeout=15)
        resp.encoding = 'utf-8'

        nav_data = _extract_json_array(resp.text, 'Data_netWorthTrend')
        acc_data = _extract_json_array(resp.text, 'Data_ACWorthTrend')

        acc_dict = {}
        if acc_data:
            for item in acc_data:
                if isinstance(item, list) and len(item) >= 2:
                    acc_dict[item[0]] = item[1]
                elif isinstance(item, dict):
                    acc_dict[item["x"]] = item["y"]

        # 存储到缓存
        conn = get_db()
        cursor = conn.cursor()
        result = []
        cutoff_ms = cutoff_date = datetime.now().timestamp() * 1000 - days * 86400000

        for item in nav_data:
            if item["x"] >= cutoff_ms:
                date_str = datetime.fromtimestamp(item["x"] / 1000).strftime("%Y-%m-%d")
                nav = round(item["y"], 4)
                acc_nav = round(acc_dict.get(item["x"], 0), 4)
                result.append({"date": date_str, "nav": nav, "acc_nav": acc_nav, "daily_return": 0})

        # 计算日收益率
        for i in range(1, len(result)):
            if result[i-1]["nav"] > 0:
                result[i]["daily_return"] = round(
                    (result[i]["nav"] - result[i-1]["nav"]) / result[i-1]["nav"] * 100, 2)

        if result:
            result[0]["daily_return"] = 0

        # 写入缓存
        for r in result[-days:]:
            cursor.execute("""
                INSERT OR REPLACE INTO nav_cache (fund_code, date, unit_nav, acc_nav, daily_return)
                VALUES (?, ?, ?, ?, ?)
            """, (fund_code, r["date"], r["nav"], r["acc_nav"], r["daily_return"]))

        conn.commit()
        conn.close()
        return result[-days:]
    except Exception as e:
        print(f"[sync] NAV fetch failed {fund_code}: {e}")

    # 返回任何可用的缓存数据
    if cached:
        return [{"date": r["date"], "nav": r["unit_nav"], "acc_nav": r["acc_nav"], "daily_return": r["daily_return"]} for r in cached]
    return []


@router.get("/all")
async def sync_all():
    """聚合返回所有页面数据。核心优化：内存缓存+DB缓存+并发拉取"""
    # 内存缓存：30秒内直接返回
    cached = _cached_sync()
    if cached:
        return cached

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # === 步骤1: 并发拉取每个unique基金的净值历史 ===
    unique_codes = list(set(h["fund_code"] for h in rows))
    fund_nav_cache = {}
    # 先用缓存，缓存miss的才并发拉取
    need_fetch = []
    for code in unique_codes:
        cached = _get_nav_from_db(code, 365)
        if cached and len(cached) >= 3:
            fund_nav_cache[code] = cached
        else:
            need_fetch.append(code)

    if need_fetch:
        futures = {EXECUTOR.submit(_get_nav_history_cached, code, 365): code for code in need_fetch}
        for future in as_completed(futures, timeout=30):
            code = futures[future]
            try:
                fund_nav_cache[code] = future.result()
            except Exception as e:
                print(f"[sync] parallel fetch failed {code}: {e}")
                fund_nav_cache[code] = []

    # === 步骤2: 基于缓存的NAV计算所有持仓数据 ===
    holdings_data = []
    total_cost = 0
    total_value = 0
    daily_values = {}

    for h in rows:
        code = h["fund_code"]
        nav_history = fund_nav_cache.get(code, [])
        latest_nav = nav_history[-1]["nav"] if nav_history else 0
        daily_return = nav_history[-1]["daily_return"] if nav_history else 0
        nav_date = nav_history[-1]["date"] if nav_history else ""

        # 计算当前市值和盈亏
        if h["buy_shares"] > 0:
            shares = h["buy_shares"]
        elif h.get("buy_nav", 0) > 0 and latest_nav > 0:
            shares = h["buy_amount"] / h["buy_nav"]
        elif latest_nav > 0 and h.get("buy_date"):
            # 用买入日的净值估算份额（从历史数据中查找）
            buy_nav = latest_nav  # fallback
            for n in nav_history:
                if n["date"] <= h["buy_date"]:
                    buy_nav = n["nav"]
            shares = h["buy_amount"] / buy_nav if buy_nav > 0 else 0
        elif latest_nav > 0:
            # 没有买入日期，假设买入成本等于当前净值（盈亏≈0是合理的）
            shares = h["buy_amount"] / latest_nav
        else:
            shares = 0

        current_value = latest_nav * shares if shares > 0 else h["buy_amount"]
        profit = current_value - h["buy_amount"]
        profit_pct = (profit / h["buy_amount"] * 100) if h["buy_amount"] > 0 else 0

        total_cost += h["buy_amount"]
        total_value += current_value

        holdings_data.append({
            "id": h["id"],
            "fund_code": code,
            "fund_name": h.get("fund_name", ""),
            "fund_type": h.get("fund_type", ""),
            "buy_amount": h["buy_amount"],
            "buy_shares": h["buy_shares"],
            "buy_nav": h.get("buy_nav", 0),
            "buy_date": h.get("buy_date", ""),
            "current_nav": round(latest_nav, 4),
            "current_value": round(current_value, 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 2),
            "daily_return": round(daily_return, 2),
            "nav_date": nav_date,
        })

        # 累积每日总市值
        for nav in nav_history:
            date = nav["date"]
            val = nav["nav"] * shares if shares > 0 else h["buy_amount"]
            daily_values[date] = daily_values.get(date, 0) + val

    # === 步骤3: 收益曲线 ===
    daily_profit = []
    for date in sorted(daily_values.keys())[-30:]:
        tv = daily_values[date]
        daily_profit.append({
            "date": date,
            "total_value": round(tv, 2),
            "total_cost": round(total_cost, 2),
            "profit": round(tv - total_cost, 2),
            "profit_pct": round((tv - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0,
        })

    # 月度收益
    monthly_data = {}
    for d in daily_profit:
        month = d["date"][:7]
        if month not in monthly_data:
            monthly_data[month] = {"month": month, "start": d["total_value"], "end": d["total_value"]}
        monthly_data[month]["end"] = d["total_value"]

    monthly_profit = []
    for m in sorted(monthly_data.keys())[-12:]:
        md = monthly_data[m]
        p = md["end"] - md["start"]
        monthly_profit.append({
            "month": m,
            "start_value": round(md["start"], 2),
            "end_value": round(md["end"], 2),
            "profit": round(p, 2),
            "profit_pct": round(p / md["start"] * 100, 2) if md["start"] > 0 else 0,
        })

    # 盈亏排行
    sorted_h = sorted(holdings_data, key=lambda x: x["profit_pct"], reverse=True)

    # === 步骤4: 市场行情（可能被缓存到数据库） ===
    indices = get_index_quotes()
    sectors = get_sector_quotes()[:8]

    # === 步骤5: 分析建议 ===
    total_profit = total_value - total_cost
    diagnosis = diagnose_portfolio(rows) if rows else []
    allocation = recommend_allocation(rows) if rows else {"recommended": {}, "current": {}, "adjustments": []}
    signals = generate_trade_signals(rows) if rows else []
    risk = assess_risk(rows) if rows else {"risk_level": "低", "risk_score": 0}

    result = {
        "summary": {
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_pct": round((total_profit / total_cost * 100) if total_cost > 0 else 0, 2),
            "fund_count": len(holdings_data),
            "details": sorted(holdings_data, key=lambda x: x["profit"], reverse=True),
        },
        "daily_profit": daily_profit,
        "monthly_profit": monthly_profit,
        "ranking": {
            "profit": [h for h in sorted_h if h["profit"] > 0],
            "loss": [h for h in sorted_h if h["profit"] < 0],
        },
        "indices": indices,
        "sectors": sectors,
        "diagnosis": diagnosis,
        "allocation": allocation,
        "signals": signals,
        "risk": risk,
    }
    _mem_cache["data"] = result
    _mem_cache["time"] = datetime.now().timestamp()
    return result
