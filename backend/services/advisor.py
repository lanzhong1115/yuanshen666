"""投资建议与诊断服务"""

from database import get_db
from services.fund_data import get_fund_latest_nav, get_fund_nav_history, get_fund_sector_allocation
from services.calculator import calculate_holding_profit


def diagnose_portfolio(holdings: list) -> list:
    """持仓诊断"""
    diagnosis = []

    # 1. 集中度检查
    total_amount = sum(h["buy_amount"] for h in holdings)
    if total_amount == 0:
        return []

    for h in holdings:
        ratio = h["buy_amount"] / total_amount * 100
        if ratio > 30:
            diagnosis.append({
                "type": "concentration",
                "level": "warning",
                "fund_code": h["fund_code"],
                "fund_name": h["fund_name"],
                "message": f"{h['fund_name']} 仓位占比 {ratio:.1f}%，过于集中，建议分散风险",
                "ratio": round(ratio, 1),
            })

    # 2. 基金数量检查
    if len(holdings) == 1:
        diagnosis.append({
            "type": "diversification",
            "level": "danger",
            "message": "仅持有1只基金，风险过于集中，建议持有3-8只不同类型基金",
        })
    elif len(holdings) > 15:
        diagnosis.append({
            "type": "diversification",
            "level": "info",
            "message": f"持有{len(holdings)}只基金，数量偏多，建议精简以方便管理",
        })

    # 3. 亏损检查
    for h in holdings:
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"]
        )
        if profit_info["profit_pct"] < -15:
            diagnosis.append({
                "type": "loss",
                "level": "danger",
                "fund_code": h["fund_code"],
                "fund_name": h["fund_name"],
                "message": f"{h['fund_name']} 亏损 {profit_info['profit_pct']:.1f}%，建议评估是否止损",
                "loss_pct": round(profit_info["profit_pct"], 1),
            })
        elif profit_info["profit_pct"] < -5:
            diagnosis.append({
                "type": "loss",
                "level": "warning",
                "fund_code": h["fund_code"],
                "fund_name": h["fund_name"],
                "message": f"{h['fund_name']} 亏损 {profit_info['profit_pct']:.1f}%，建议持续关注",
                "loss_pct": round(profit_info["profit_pct"], 1),
            })

    return diagnosis


def recommend_allocation(holdings: list) -> dict:
    """推荐分仓比例"""
    total_amount = sum(h["buy_amount"] for h in holdings)

    # 默认推荐配置（基于风险平价的简化版）
    recommended = {
        "stock": 40,       # 股票型
        "mixed": 30,       # 混合型
        "bond": 20,        # 债券型
        "money": 10,       # 货币型
    }

    # 如果用户已有持仓，根据实际情况调整
    current_allocation = {"stock": 0, "mixed": 0, "bond": 0, "money": 0, "other": 0}

    for h in holdings:
        ftype = h.get("fund_type", "")
        amount = h["buy_amount"]
        if "股票" in ftype or "指数" in ftype or "ETF" in ftype:
            current_allocation["stock"] += amount
        elif "混合" in ftype:
            current_allocation["mixed"] += amount
        elif "债券" in ftype or "债" in ftype:
            current_allocation["bond"] += amount
        elif "货币" in ftype or "货基" in ftype or "短债" in ftype:
            current_allocation["money"] += amount
        else:
            current_allocation["other"] += amount

    # 转为百分比
    if total_amount > 0:
        for k in current_allocation:
            current_allocation[k] = round(current_allocation[k] / total_amount * 100, 1)

    # 调整建议
    adjustments = []
    if current_allocation["stock"] > 60:
        adjustments.append("股票型基金占比较高，建议适当增加债券型配置以降低波动")
    if current_allocation["bond"] < 10 and total_amount > 0:
        adjustments.append("建议增加债券型基金作为安全垫")
    if current_allocation["money"] < 5 and total_amount > 0:
        adjustments.append("建议保留至少5%的货币基金作为流动资金")

    return {
        "recommended": recommended,
        "current": current_allocation,
        "adjustments": adjustments,
        "total_amount": round(total_amount, 2),
    }


def generate_trade_signals(holdings: list) -> list:
    """生成买卖参考信号"""
    signals = []

    for h in holdings:
        nav_data = get_fund_nav_history(h["fund_code"], days=60)
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"]
        )

        signal = {
            "fund_code": h["fund_code"],
            "fund_name": h["fund_name"],
            "current_profit_pct": profit_info["profit_pct"],
            "action": "hold",
            "reason": "",
            "strength": 0,
        }

        if len(nav_data) < 20:
            signal["action"] = "hold"
            signal["reason"] = "数据不足，暂无法判断"
            signals.append(signal)
            continue

        # 计算均线
        recent_navs = [d["nav"] for d in nav_data]
        current_nav = recent_navs[-1]

        ma5 = sum(recent_navs[-5:]) / 5 if len(recent_navs) >= 5 else current_nav
        ma10 = sum(recent_navs[-10:]) / 10 if len(recent_navs) >= 10 else current_nav
        ma20 = sum(recent_navs[-20:]) / 20 if len(recent_navs) >= 20 else current_nav
        ma60 = sum(recent_navs) / len(recent_navs)

        # 近一周收益
        week_return = 0
        if len(recent_navs) >= 5:
            week_return = (recent_navs[-1] - recent_navs[-5]) / recent_navs[-5] * 100

        # 近一月收益
        month_return = 0
        if len(recent_navs) >= 20:
            month_return = (recent_navs[-1] - recent_navs[-20]) / recent_navs[-20] * 100

        # 信号判断
        score = 0

        # 均线多头排列
        if current_nav > ma5 > ma10 > ma20:
            score += 2
            signal["reason"] = "均线多头排列,趋势向好"
        elif current_nav < ma5 < ma10 < ma20:
            score -= 2
            signal["reason"] = "均线空头排列,趋势走弱"

        # 金叉/死叉
        if ma5 > ma10 and len(recent_navs) >= 10:
            prev_ma5 = sum(recent_navs[-6:-1]) / 5
            prev_ma10 = sum(recent_navs[-11:-1]) / 10
            if prev_ma5 <= prev_ma10:  # 刚形成金叉
                score += 1
                signal["reason"] += "；短期均线金叉"

        # 超跌反弹机会
        if month_return < -10:
            score += 1
            signal["reason"] += "；近一月跌幅较大，可能存在超跌反弹机会"

        # 止盈提醒
        if profit_info["profit_pct"] > 30:
            score -= 1
            signal["reason"] += "；盈利丰厚，建议分批止盈"

        # 止损提醒
        if profit_info["profit_pct"] < -20:
            score -= 2
            signal["reason"] += "；亏损较大，建议评估是否止损"

        if score >= 3:
            signal["action"] = "buy"
            signal["strength"] = min(score, 5)
        elif score <= -3:
            signal["action"] = "sell"
            signal["strength"] = min(abs(score), 5)
        else:
            signal["action"] = "hold"
            signal["strength"] = 0
            if not signal["reason"]:
                signal["reason"] = "趋势不明朗，建议持有观望"

        signals.append(signal)

    return signals


def assess_risk(holdings: list) -> dict:
    """风险评估"""
    if not holdings:
        return {
            "risk_level": "低",
            "risk_score": 0,
            "suggested_position": 0,
            "factors": [],
        }

    total_amount = sum(h["buy_amount"] for h in holdings)
    risk_score = 0
    factors = []

    # 1. 基金数量因素
    fund_count = len(holdings)
    if fund_count <= 2:
        risk_score += 30
        factors.append("持仓过于集中（≤2只）")
    elif fund_count >= 8:
        risk_score -= 10
        factors.append("持仓分散良好")

    # 2. 股票型占比因素
    stock_ratio = 0
    for h in holdings:
        ftype = h.get("fund_type", "")
        if "股票" in ftype or "指数" in ftype:
            stock_ratio += h["buy_amount"]

    if total_amount > 0:
        stock_pct = stock_ratio / total_amount * 100
        if stock_pct > 80:
            risk_score += 25
            factors.append(f"股票型基金占比过高({stock_pct:.0f}%)")
        elif stock_pct > 50:
            risk_score += 10
            factors.append(f"偏股型为主({stock_pct:.0f}%)，风险适中")

    # 3. 最大亏损因素
    max_loss = 0
    for h in holdings:
        profit_info = calculate_holding_profit(
            h["fund_code"], h["buy_shares"], h["buy_amount"]
        )
        if profit_info["profit_pct"] < max_loss:
            max_loss = profit_info["profit_pct"]

    if max_loss < -20:
        risk_score += 25
        factors.append(f"单只最大亏损 {abs(max_loss):.0f}%，需关注")
    elif max_loss < -10:
        risk_score += 10
        factors.append(f"单只浮亏 {abs(max_loss):.0f}%")

    # 风险等级
    if risk_score >= 60:
        risk_level = "高"
    elif risk_score >= 30:
        risk_level = "中"
    else:
        risk_level = "低"

    # 建议仓位（风险平价简化版）
    suggested_position = max(30, 100 - risk_score)

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "suggested_position": suggested_position,
        "suggested_cash": 100 - suggested_position,
        "factors": factors,
    }
