"""分析与建议 API"""

from fastapi import APIRouter, HTTPException
from database import get_db
from services.calculator import (
    calculate_holding_profit,
    get_daily_profit_history,
    get_monthly_profit_history,
)
from services.advisor import (
    diagnose_portfolio,
    recommend_allocation,
    generate_trade_signals,
    assess_risk,
)

router = APIRouter()


@router.get("/portfolio/diagnosis")
async def portfolio_diagnosis():
    """持仓诊断"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    holdings = [dict(r) for r in rows]
    if not holdings:
        return {"message": "暂无持仓数据，请先添加持仓", "diagnosis": []}

    diagnosis = diagnose_portfolio(holdings)
    return {"diagnosis": diagnosis}


@router.get("/portfolio/allocation")
async def portfolio_allocation():
    """推荐分仓比例"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    holdings = [dict(r) for r in rows]
    allocation = recommend_allocation(holdings)
    return allocation


@router.get("/portfolio/signals")
async def trade_signals():
    """买卖信号"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    holdings = [dict(r) for r in rows]
    if not holdings:
        return {"signals": [], "message": "暂无持仓"}

    signals = generate_trade_signals(holdings)
    return {"signals": signals}


@router.get("/portfolio/risk")
async def portfolio_risk():
    """风险评估"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    holdings = [dict(r) for r in rows]
    risk = assess_risk(holdings)
    return risk


@router.get("/profit/daily")
async def daily_profit(days: int = 30):
    """每日收益历史"""
    data = get_daily_profit_history(days)
    return {"daily_profit": data}


@router.get("/profit/monthly")
async def monthly_profit(months: int = 12):
    """每月收益历史"""
    data = get_monthly_profit_history(months)
    return {"monthly_profit": data}


@router.get("/profit/ranking")
async def profit_ranking():
    """盈亏排行"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    ranking = []
    for row in rows:
        h = dict(row)
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"]
        )
        ranking.append({
            "fund_code": h["fund_code"],
            "fund_name": h["fund_name"],
            "buy_amount": h["buy_amount"],
            "current_value": profit_info["current_value"],
            "profit": profit_info["profit"],
            "profit_pct": profit_info["profit_pct"],
        })

    ranking.sort(key=lambda x: x["profit_pct"], reverse=True)
    profit_list = [r for r in ranking if r["profit"] > 0]
    loss_list = [r for r in ranking if r["profit"] < 0]

    return {
        "all": ranking,
        "profit": profit_list,
        "loss": loss_list,
    }
