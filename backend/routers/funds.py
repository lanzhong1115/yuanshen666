"""基金数据 API"""

from fastapi import APIRouter, HTTPException, Query
from database import get_db
from services.fund_data import (
    get_fund_info,
    get_fund_nav_history,
    get_fund_latest_nav,
    search_funds,
    get_fund_holdings,
    get_fund_sector_allocation,
)
from services.realtime_nav import estimate_fund_nav, estimate_holding_navs
from services.realtime_valuation import fetch_fund_valuation, fetch_batch_valuations
from typing import Optional

router = APIRouter()


@router.get("/search")
async def search(query: str = Query(..., min_length=2, description="搜索关键词（代码或名称）")):
    """搜索基金"""
    results = search_funds(query)
    return {"results": results[:20]}


@router.get("/{fund_code}/info")
async def fund_info(fund_code: str):
    """获取基金基本信息"""
    try:
        info = get_fund_info(fund_code)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/nav")
async def fund_nav(
    fund_code: str,
    days: int = Query(default=90, description="获取近N天净值数据"),
):
    """获取基金历史净值"""
    try:
        nav_data = get_fund_nav_history(fund_code, days=days)
        return {"fund_code": fund_code, "nav_data": nav_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/latest")
async def fund_latest(fund_code: str):
    """获取基金最新净值和涨跌"""
    try:
        data = get_fund_latest_nav(fund_code)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/estimate")
async def fund_estimate_nav(fund_code: str):
    """获取基金实时估算净值（基于季报持仓+实时股价）"""
    try:
        data = estimate_fund_nav(fund_code)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estimate-all")
async def estimate_all_holdings():
    """为所有持仓基金计算实时估值"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM holdings")
        rows = cursor.fetchall()
        conn.close()

        holdings = [dict(r) for r in rows]
        if not holdings:
            return {"holdings": [], "summary": None, "message": "暂无持仓"}

        results = estimate_holding_navs(holdings)

        # 汇总
        total_cost = sum(h["buy_amount"] for h in holdings)
        total_value = sum(r["current_value"] for r in results)
        total_profit = total_value - total_cost
        total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

        return {
            "holdings": results,
            "summary": {
                "total_cost": round(total_cost, 2),
                "total_value": round(total_value, 2),
                "total_profit": round(total_profit, 2),
                "total_profit_pct": round(total_profit_pct, 2),
                "fund_count": len(results),
            },
            "updated_at": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/holdings")
async def fund_portfolio(fund_code: str, year: str = "2026"):
    """获取基金前十大持仓"""
    try:
        data = get_fund_holdings(fund_code, year)
        return {"fund_code": fund_code, "holdings": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/detail")
async def fund_detail(fund_code: str, include_estimate: bool = False, days: int = 365):
    """获取基金完整详情"""
    try:
        info = get_fund_info(fund_code)
        nav_history = get_fund_nav_history(fund_code, days=days)
        holdings = get_fund_holdings(fund_code)

        # 1月/3月/6月/1年收益率
        returns = {}
        if nav_history:
            ln = nav_history[-1]["nav"]
            for label, offset in [("1月", 22), ("3月", 66), ("6月", 132), ("1年", 264)]:
                if len(nav_history) > offset and nav_history[-offset]["nav"] > 0:
                    returns[label] = round((ln - nav_history[-offset]["nav"]) / nav_history[-offset]["nav"] * 100, 2)

        result = {
            "fund_code": fund_code,
            "fund_name": info.get("fund_name", ""),
            "fund_type": info.get("fund_type", ""),
            "latest_nav": info.get("latest_nav", 0),
            "latest_date": info.get("latest_date", ""),
            "nav_history": nav_history[-90:],
            "holdings": holdings,
            "sectors": [],
            "returns": returns,
        }
        if include_estimate:
            result["estimate"] = estimate_fund_nav(fund_code)
        # 实时估值（天天基金 fundgz）
        try:
            val = fetch_fund_valuation(fund_code)
            if val:
                result["valuation"] = val
        except Exception:
            pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/valuation")
async def fund_valuation(fund_code: str):
    """获取基金实时估值（天天基金 fundgz）"""
    try:
        data = fetch_fund_valuation(fund_code)
        if not data:
            raise HTTPException(status_code=404, detail="无法获取实时估值（可能非交易时段或基金不支持）")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/valuations")
async def batch_valuations(codes: list[str]):
    """批量获取基金实时估值"""
    try:
        results = fetch_batch_valuations(codes)
        return {"valuations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fund_code}/sectors")
async def fund_sectors(fund_code: str):
    """获取基金行业配置"""
    try:
        data = get_fund_sector_allocation(fund_code)
        return {"fund_code": fund_code, "sectors": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
