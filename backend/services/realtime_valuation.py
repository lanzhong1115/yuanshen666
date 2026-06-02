"""实时估值服务 — 对接天天基金 fundgz JSONP API

数据来源: https://fundgz.1234567.com.cn/js/{code}.js
返回格式: jsonpgz({"fundcode":"...","name":"...","jzrq":"...","dwjz":"...","gsz":"...","gszzl":"...","gztime":"..."})

缓存策略:
- 交易日 9:25-15:05: 30秒
- 非交易时段: 5分钟
"""

import re
import json
import time
import threading
from datetime import datetime

import requests

# 内存缓存
_cache = {}
_cache_lock = threading.Lock()

# A股交易日历缓存（简单判断：周一至周五，排除明显节假日，后续可接入交易日历API）
def _is_trading_time() -> bool:
    """判断当前是否在A股交易时段（含前后5分钟冗余）"""
    now = datetime.now()
    day = now.weekday()  # 0=Mon, 6=Sun
    if day >= 5:
        return False
    t = now.hour * 100 + now.minute
    return (925 <= t <= 1135) or (1255 <= t <= 1505)

def _get_cache_ttl() -> float:
    """获取估值缓存时长（秒）: 交易时段30s, 非交易5min"""
    return 30 if _is_trading_time() else 300


def _parse_jsonp(text: str) -> dict | None:
    """解析 jsonpgz({...}) 格式的JSONP响应"""
    if not text:
        return None
    m = re.search(r'jsonpgz\((.+)\)', text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def fetch_fund_valuation(code: str) -> dict | None:
    """获取单只基金实时估值

    Returns:
        dict with keys: fundcode, name, jzrq, dwjz, gsz, gszzl, gztime, valuation_source
        or None if failed
    """
    code = str(code).strip()
    if not code:
        return None

    # 检查缓存
    now = time.time()
    with _cache_lock:
        cached = _cache.get(code)
        if cached and (now - cached["_ts"]) < _get_cache_ttl():
            return {k: v for k, v in cached.items() if k != "_ts"}

    # 请求 fundgz API
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(now * 1000)}"
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://fundf10.eastmoney.com/"
        }, timeout=10)
        resp.raise_for_status()
        data = _parse_jsonp(resp.text)
        if not data:
            return None

        # 规范化
        result = {
            "fundcode": data.get("fundcode", code),
            "name": data.get("name", ""),
            "jzrq": data.get("jzrq", ""),           # 净值日期
            "dwjz": data.get("dwjz", ""),            # 单位净值
            "gsz": data.get("gsz", ""),              # 估算净值
            "gszzl": data.get("gszzl", ""),          # 估算涨跌幅(%)
            "gztime": data.get("gztime", ""),        # 估值时间
            "valuation_source": "fundgz"
        }

        # 将字符串转为数值
        for k in ("dwjz", "gsz", "gszzl"):
            try:
                result[k] = float(result[k])
            except (ValueError, TypeError):
                result[k] = None

        # 写入缓存
        with _cache_lock:
            result["_ts"] = now
            _cache[code] = result

        return {k: v for k, v in result.items() if k != "_ts"}

    except Exception as e:
        # 如果有过期缓存，返回过期缓存
        with _cache_lock:
            cached = _cache.get(code)
            if cached:
                result = {k: v for k, v in cached.items() if k != "_ts"}
                result["_stale"] = True
                return result
        return None


def fetch_batch_valuations(codes: list[str]) -> dict[str, dict]:
    """批量获取基金实时估值

    Args:
        codes: 基金代码列表

    Returns:
        {code: valuation_dict} — 只包含成功获取的基金
    """
    import concurrent.futures

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_fund_valuation, c): c for c in codes}
        for future in concurrent.futures.as_completed(futures):
            code = futures[future]
            try:
                val = future.result()
                if val:
                    results[code] = val
            except Exception:
                pass
    return results
