"""实时估值 - 从缓存获取最新净值变化"""
from services.fund_data import get_fund_latest_nav, get_fund_holdings
from datetime import datetime

def estimate_fund_nav(fund_code: str) -> dict:
    """获取基金最新净值和日涨幅（从缓存，<0.1s）"""
    latest = get_fund_latest_nav(fund_code)
    nav = latest.get("nav", 0)
    date = latest.get("date", "")
    dret = latest.get("daily_return", 0)

    # 简单持仓信息（只查季报，不做实时股价）
    holdings = []
    for year in [str(datetime.now().year), str(datetime.now().year - 1)]:
        holdings = get_fund_holdings(fund_code, year)
        if holdings: break

    # 实时估值 ≈ 收盘净值 + 日涨跌（净值每天更新一次，这是最准的"实时"数据）
    estimated_nav = nav
    if nav > 0 and dret != 0:
        estimated_nav = round(nav * (1 + dret / 100), 4)

    return {
        "fund_code": fund_code,
        "estimated_nav": estimated_nav,
        "estimated_change_pct": round(dret, 2),
        "last_nav": round(nav, 4),
        "last_nav_date": date,
        "confidence": 70 if holdings else 0,
        "total_disclosed_ratio": sum(h.get("ratio", 0) for h in holdings[:10]),
        "holdings_detail": holdings[:10],
        "message": "基于最新季报持仓，实时股价需在交易时间查看",
    }

def estimate_holding_navs(holdings: list) -> list:
    """批量获取持仓估值"""
    results = []
    for h in holdings:
        est = estimate_fund_nav(h["fund_code"])
        nav = est["estimated_nav"] if est["estimated_nav"] > 0 else est["last_nav"]
        shares = h.get("buy_shares", 0)
        if not shares and nav > 0:
            shares = h["buy_amount"] / nav if h.get("buy_nav", 0) <= 0 else h["buy_amount"] / h["buy_nav"]
        results.append({
            **est,
            "holding_id": h.get("id"),
            "fund_name": h.get("fund_name", ""),
            "buy_amount": h.get("buy_amount", 0),
            "current_value": round(nav * shares, 2) if shares > 0 else h.get("buy_amount", 0),
            "profit": round(nav * shares - h.get("buy_amount", 0), 2) if shares > 0 else 0,
            "profit_pct": round((nav * shares - h.get("buy_amount", 0)) / h.get("buy_amount", 0) * 100, 2) if shares > 0 and h.get("buy_amount", 0) > 0 else 0,
        })
    return results
