"""盈亏计算服务"""

from datetime import datetime, timedelta
from database import get_db
from services.fund_data import get_fund_latest_nav, get_fund_nav_history


def calculate_holding_profit(fund_code: str, buy_shares: float, buy_amount: float, buy_nav: float = 0, buy_date: str = '') -> dict:
    """计算单只基金持仓盈亏

    修复了份额为空时的计算bug:
    - 有份额: current_value = current_nav * buy_shares
    - 无份额但有买入净值: 反推份额 = buy_amount / buy_nav, 再算市值
    - 都没有: 用最新净值反推(近似, 盈亏接近0)
    """
    latest = get_fund_latest_nav(fund_code)

    current_nav = latest.get("nav", 0)
    daily_return = latest.get("daily_return", 0)
    nav_date = latest.get("date", "")

    current_value = 0
    profit = 0
    profit_pct = 0

    if current_nav <= 0:
        # 没有净值数据, 无法计算
        return {
            "current_nav": 0,
            "current_value": round(buy_amount, 2),
            "profit": 0,
            "profit_pct": 0,
            "daily_return": 0,
            "nav_date": nav_date,
        }

    if buy_shares > 0:
        # 有份额: 精确计算
        current_value = current_nav * buy_shares
        profit = current_value - buy_amount
        profit_pct = (profit / buy_amount * 100) if buy_amount > 0 else 0
    elif buy_nav > 0 and buy_amount > 0:
        # 有买入净值: 反推份额再算
        estimated_shares = buy_amount / buy_nav
        current_value = current_nav * estimated_shares
        profit = current_value - buy_amount
        profit_pct = (profit / buy_amount * 100) if buy_amount > 0 else 0
    elif buy_amount > 0:
        # 没有任何参考: 从历史净值推算买入价
        nav_history = get_fund_nav_history(fund_code, days=180)
        # 找买入日附近的净值
        buy_nav_estimated = current_nav
        if buy_date and nav_history:
            for n in nav_history:
                if n['date'] <= buy_date:
                    buy_nav_estimated = n['nav']
        if buy_nav_estimated > 0:
            estimated_shares = buy_amount / buy_nav_estimated
            current_value = current_nav * estimated_shares
            profit = current_value - buy_amount
            profit_pct = (profit / buy_amount * 100) if buy_amount > 0 else 0
        else:
            current_value = buy_amount
            profit = 0
            profit_pct = 0

    return {
        "current_nav": round(current_nav, 4),
        "current_value": round(current_value, 2),
        "profit": round(profit, 2),
        "profit_pct": round(profit_pct, 2),
        "daily_return": round(daily_return, 2),
        "nav_date": nav_date,
    }


def get_latest_trading_date() -> str:
    """获取最近的交易日日期（考虑周末）"""
    today = datetime.now()
    # 简单处理: 周六回退到周五, 周日回退到周五
    weekday = today.weekday()  # 0=Mon, 6=Sun
    if weekday == 5:  # Saturday
        today = today - timedelta(days=1)
    elif weekday == 6:  # Sunday
        today = today - timedelta(days=2)
    return today.strftime("%Y-%m-%d")


def get_daily_profit_history(days: int = 30) -> list:
    """获取每日收益历史（基于持仓净值变化计算）

    修复: 当日没有数据时使用最近一个交易日的数据
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    holdings = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not holdings:
        # 从缓存表读取
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM daily_profit ORDER BY date DESC LIMIT ?",
            (days,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    # 计算每日总市值（基于净值历史）
    daily_values = {}
    total_cost = 0

    for h in holdings:
        total_cost += h["buy_amount"]
        nav_data = get_fund_nav_history(h["fund_code"], days=days)

        # determine effective shares for this holding
        if h["buy_shares"] > 0:
            shares = h["buy_shares"]
        elif h.get("buy_nav", 0) > 0 and h["buy_amount"] > 0:
            shares = h["buy_amount"] / h["buy_nav"]
        elif nav_data and nav_data[-1]["nav"] > 0:
            shares = h["buy_amount"] / nav_data[-1]["nav"]
        else:
            shares = 0

        for nav in nav_data:
            date = nav["date"]
            value = nav["nav"] * shares if shares > 0 else h["buy_amount"]
            if date not in daily_values:
                daily_values[date] = {"total_value": 0, "total_cost": total_cost}
            daily_values[date]["total_value"] += value

    if not daily_values:
        return []

    # 找到最近有数据的日期
    latest_date = get_latest_trading_date()
    available_dates = sorted(daily_values.keys())
    display_date = latest_date
    if latest_date not in daily_values and available_dates:
        display_date = available_dates[-1]  # 使用最近可用日期

    results = []
    for date in sorted(daily_values.keys()):
        tv = daily_values[date]["total_value"]
        results.append({
            "date": date,
            "total_value": round(tv, 2),
            "total_cost": round(total_cost, 2),
            "profit": round(tv - total_cost, 2),
            "profit_pct": round((tv - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0,
        })

    return results[-days:]


def get_monthly_profit_history(months: int = 12) -> list:
    """获取每月收益历史"""
    daily_data = get_daily_profit_history(days=months * 31)
    monthly = {}
    for item in daily_data:
        month = item["date"][:7]  # YYYY-MM
        if month not in monthly:
            monthly[month] = {
                "month": month,
                "start_value": item["total_value"],
                "end_value": item["total_value"],
                "total_cost": item["total_cost"],
            }
        monthly[month]["end_value"] = item["total_value"]

    results = []
    for month in sorted(monthly.keys()):
        m = monthly[month]
        profit = m["end_value"] - m["start_value"]
        results.append({
            "month": month,
            "start_value": round(m["start_value"], 2),
            "end_value": round(m["end_value"], 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit / m["start_value"] * 100, 2) if m["start_value"] > 0 else 0,
        })

    return results[-months:]


def save_daily_profit():
    """保存当日收益快照（由调度器调用）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    holdings = [dict(r) for r in cursor.fetchall()]

    if not holdings:
        conn.close()
        return

    total_value = 0
    total_cost = 0
    for h in holdings:
        total_cost += h["buy_amount"]
        latest = get_fund_latest_nav(h["fund_code"])
        nav = latest.get("nav", 0)

        if nav > 0:
            if h["buy_shares"] > 0:
                total_value += nav * h["buy_shares"]
            elif h.get("buy_nav", 0) > 0:
                shares = h["buy_amount"] / h["buy_nav"]
                total_value += nav * shares
            else:
                total_value += h["buy_amount"]

    today = get_latest_trading_date()
    profit = total_value - total_cost
    profit_pct = (profit / total_cost * 100) if total_cost > 0 else 0

    cursor.execute("""
        INSERT OR REPLACE INTO daily_profit (date, total_value, total_cost, profit, profit_pct)
        VALUES (?, ?, ?, ?, ?)
    """, (today, round(total_value, 2), round(total_cost, 2), round(profit, 2), round(profit_pct, 2)))
    conn.commit()
    conn.close()
