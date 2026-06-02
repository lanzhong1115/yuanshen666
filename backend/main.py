"""养基助手 v2.4 — FastAPI 主入口"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from database import init_db

app = FastAPI(title="养基助手", version="2.4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from routers import holdings, funds, market, analysis, sync
app.include_router(holdings.router, prefix="/api/holdings")
app.include_router(funds.router, prefix="/api/funds")
app.include_router(market.router, prefix="/api/market")
app.include_router(analysis.router, prefix="/api/analysis")
app.include_router(sync.router, prefix="/api/sync")

@app.on_event("startup")
async def startup():
    init_db()
    # 后台预热缓存：启动后直接调用sync填充内存缓存
    import threading
    def warmup():
        import time
        time.sleep(5)
        try:
            from routers.sync import sync_all
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(sync_all())
            loop.close()
        except: pass
    threading.Thread(target=warmup, daemon=True).start()

@app.get("/api/health")
async def health(): return {"status": "ok"}

static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
