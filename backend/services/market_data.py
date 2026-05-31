"""市场行情 — 绝对不会崩溃"""
import httpx
from database import get_db

INDEX_CONFIG = {
    "1.000001":"上证指数","0.399001":"深证成指","0.399006":"创业板指",
    "1.000688":"科创50","0.399005":"中小100","1.000300":"沪深300",
    "1.000905":"中证500","1.000852":"中证1000",
}

def _safe_get(url):
    try: return httpx.get(url, timeout=5)
    except: return None

def get_index_quotes():
    try:
        secids = ",".join(INDEX_CONFIG.keys())
        url = f"http://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids={secids}&fields=f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18"
        resp = _safe_get(url)
        if not resp: return _cached_indices()
        data = resp.json()
        if not data.get("data") or not data["data"].get("diff"): return _cached_indices()
        results = []
        for item in data["data"]["diff"]:
            results.append({
                "code":item.get("f12",""), "name":INDEX_CONFIG.get(item.get("f12",""),item.get("f14","")),
                "price":round(item.get("f2",0),2), "change_pct":round(item.get("f3",0),2),
                "change_amt":round(item.get("f4",0),2), "volume":item.get("f5",0),
                "high":round(item.get("f15",0),2), "low":round(item.get("f16",0),2),
                "open":round(item.get("f17",0),2), "prev_close":round(item.get("f18",0),2),
            })
        conn=get_db(); c=conn.cursor()
        for r in results: c.execute("INSERT OR REPLACE INTO index_cache VALUES(?,?,?,?,?,?,?,?,?,?)", [r["code"],r["name"],r["price"],r["change_pct"],r["change_amt"],r["volume"],r["high"],r["low"],r["open"],r["prev_close"]])
        conn.commit(); conn.close()
        return results
    except: return _cached_indices()

def _cached_indices():
    try:
        conn=get_db(); rows=conn.execute("SELECT * FROM index_cache").fetchall(); conn.close()
        return [dict(r) for r in rows]
    except: return []

def get_sector_quotes():
    try:
        resp = _safe_get("http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=30&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f2,f3,f12,f14")
        if not resp: return []
        data = resp.json()
        if not data.get("data") or not data["data"].get("diff"): return []
        return [{"code":i["f12"],"name":i["f14"],"price":round(i.get("f2",0),2),"change_pct":round(i.get("f3",0),2)} for i in data["data"]["diff"]]
    except: return []

def get_sector_flow():
    try:
        resp = _safe_get("http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=30&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f2,f3,f12,f14,f62")
        if not resp: return []
        data = resp.json()
        if not data.get("data") or not data["data"].get("diff"): return []
        return [{"code":i["f12"],"name":i["f14"],"change_pct":round(i.get("f3",0),2),"main_inflow":round(i.get("f62",0)/1e8,2) if i.get("f62") else 0} for i in data["data"]["diff"]]
    except: return []
