"""持仓管理 API"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import get_db
from services.calculator import calculate_holding_profit
from services.realtime_nav import estimate_holding_navs

router = APIRouter()


class HoldingCreate(BaseModel):
    fund_code: str
    fund_name: str = ""
    fund_type: str = ""
    buy_amount: float = 0
    buy_shares: float = 0
    buy_nav: float = 0
    buy_date: str = ""
    platform: str = "手动录入"
    notes: str = ""


class HoldingUpdate(BaseModel):
    fund_name: Optional[str] = None
    fund_type: Optional[str] = None
    buy_amount: Optional[float] = None
    buy_shares: Optional[float] = None
    buy_nav: Optional[float] = None
    buy_date: Optional[str] = None
    platform: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def list_holdings():
    """获取所有持仓（含实时盈亏计算）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings ORDER BY created_at DESC")
    rows = cursor.fetchall()
    holdings = []
    for row in rows:
        h = dict(row)
        # 计算盈亏
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"], h.get("buy_nav", 0), h.get("buy_date", "")
        )
        h.update(profit_info)
        holdings.append(h)
    conn.close()
    return {"holdings": holdings, "count": len(holdings)}


@router.post("/")
async def add_holding(data: HoldingCreate):
    """添加持仓"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO holdings (fund_code, fund_name, fund_type, buy_amount,
            buy_shares, buy_nav, buy_date, platform, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.fund_code, data.fund_name, data.fund_type,
        data.buy_amount, data.buy_shares, data.buy_nav,
        data.buy_date, data.platform, data.notes
    ))
    conn.commit()
    holding_id = cursor.lastrowid
    conn.close()
    return {"id": holding_id, "message": "持仓添加成功"}


@router.put("/{holding_id}")
async def update_holding(holding_id: int, data: HoldingUpdate):
    """更新持仓"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings WHERE id = ?", (holding_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="持仓记录不存在")

    updates = {k: v for k, v in data.dict().items() if v is not None}
    if updates:
        updates["updated_at"] = "datetime('now', 'localtime')"
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        cursor.execute(
            f"UPDATE holdings SET {set_clause} WHERE id = ?",
            list(updates.values()) + [holding_id]
        )
        conn.commit()
    conn.close()
    return {"message": "更新成功"}


@router.delete("/{holding_id}")
async def delete_holding(holding_id: int):
    """删除持仓"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings WHERE id = ?", (holding_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="持仓记录不存在")
    cursor.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
    conn.commit()
    conn.close()
    return {"message": "删除成功"}


class TradeData(BaseModel):
    type: str       # 'buy' or 'sell' or 'auto'
    amount: float = 0
    shares: float = 0
    nav: float = 0
    date: str = ""
    notes: str = ""

@router.post("/{holding_id}/trade")
async def add_trade(holding_id: int, data: TradeData):
    """加仓/减仓/定投"""
    conn = get_db()
    cursor = conn.cursor()
    h = cursor.execute("SELECT * FROM holdings WHERE id = ?", (holding_id,)).fetchone()
    if not h:
        conn.close()
        raise HTTPException(status_code=404, detail="持仓不存在")

    h = dict(h)
    if data.type == 'buy':
        new_shares = h["buy_shares"] + data.shares
        new_amount = h["buy_amount"] + data.amount
        cursor.execute("UPDATE holdings SET buy_shares=?, buy_amount=?, updated_at=datetime('now','localtime') WHERE id=?",
                       [new_shares, new_amount, holding_id])
    elif data.type == 'sell':
        new_shares = max(0, h["buy_shares"] - data.shares)
        ratio = data.shares / h["buy_shares"] if h["buy_shares"] > 0 else 0
        new_amount = max(0, h["buy_amount"] - h["buy_amount"] * ratio)
        cursor.execute("UPDATE holdings SET buy_shares=?, buy_amount=?, updated_at=datetime('now','localtime') WHERE id=?",
                       [new_shares, round(new_amount,2), holding_id])
    elif data.type == 'auto':
        auto_info = f"{data.notes},{data.amount}" if data.notes else str(data.amount)
        cursor.execute("UPDATE holdings SET auto_invest=?, updated_at=datetime('now','localtime') WHERE id=?",
                       [auto_info, holding_id])

    # Record trade
    cursor.execute("INSERT INTO trades (holding_id,fund_code,type,amount,shares,nav,date,notes) VALUES (?,?,?,?,?,?,?,?)",
                   [holding_id, h["fund_code"], data.type, data.amount, data.shares, data.nav, data.date, data.notes])
    conn.commit()
    conn.close()
    return {"message": f"{'加仓' if data.type=='buy' else '减仓' if data.type=='sell' else '定投'}成功"}

@router.get("/{holding_id}/trades")
async def get_trades(holding_id: int):
    """获取交易记录"""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM trades WHERE holding_id=? ORDER BY date DESC", (holding_id,)).fetchall()
    conn.close()
    return {"trades": [dict(r) for r in rows]}


@router.get("/summary")
async def holdings_summary(realtime: bool = Query(default=False, description="是否使用实时估值计算")):
    """持仓汇总（总资产、总盈亏等）

    当 realtime=true 时，通过基金季报持仓+实时股价反算实时估算净值
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings")
    rows = cursor.fetchall()
    conn.close()

    holdings_data = [dict(row) for row in rows]

    if not holdings_data:
        return {
            "total_cost": 0, "total_value": 0, "total_profit": 0,
            "total_profit_pct": 0, "fund_count": 0, "details": [],
            "is_estimated": False,
        }

    # 使用实时估值
    if realtime:
        try:
            estimated = estimate_holding_navs(holdings_data)
            total_cost = sum(h["buy_amount"] for h in holdings_data)
            total_value = sum(e["current_value"] for e in estimated)
            total_profit = total_value - total_cost
            total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

            details = []
            for e in estimated:
                h_orig = next((h for h in holdings_data if h["id"] == e.get("holding_id")), {})
                details.append({
                    "id": e.get("holding_id"),
                    "fund_code": e["fund_code"],
                    "fund_name": e.get("fund_name", ""),
                    "fund_type": h_orig.get("fund_type", ""),
                    "buy_amount": e.get("buy_amount", 0),
                    "buy_shares": e.get("buy_shares", 0),
                    "buy_nav": h_orig.get("buy_nav", 0),
                    "buy_date": h_orig.get("buy_date", ""),
                    "current_nav": e["estimated_nav"],
                    "current_value": e["current_value"],
                    "profit": e["profit"],
                    "profit_pct": e["profit_pct"],
                    "daily_return": e.get("estimated_change_pct", 0),
                    "nav_date": e.get("last_nav_date", ""),
                    "confidence": e.get("confidence", 0),
                    "message": e.get("message", ""),
                    "is_estimated": True,
                })

            details.sort(key=lambda x: x["profit"], reverse=True)

            return {
                "total_cost": round(total_cost, 2),
                "total_value": round(total_value, 2),
                "total_profit": round(total_profit, 2),
                "total_profit_pct": round(total_profit_pct, 2),
                "fund_count": len(details),
                "details": details,
                "is_estimated": True,
            }
        except Exception as e:
            print(f"[holdings] 实时估值失败，回退到收盘净值: {e}")

    # 使用收盘净值（默认）
    total_cost = 0
    total_value = 0
    total_profit = 0
    details = []

    for row in rows:
        h = dict(row)
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"], h.get("buy_nav", 0), h.get("buy_date", "")
        )
        total_cost += h["buy_amount"]
        total_value += profit_info["current_value"]
        total_profit += profit_info["profit"]
        h.update(profit_info)
        h["is_estimated"] = False
        details.append(h)

    total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_pct": round(total_profit_pct, 2),
        "fund_count": len(details),
        "details": sorted(details, key=lambda x: x["profit"], reverse=True),
        "is_estimated": False,
    }
