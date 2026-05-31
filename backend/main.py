"""养基助手 - FastAPI 主入口"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from database import init_db

app = FastAPI(title="养基助手", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 路由注册
from routers import holdings, funds, market, analysis, sync
app.include_router(holdings.router, prefix="/api/holdings")
app.include_router(funds.router, prefix="/api/funds")
app.include_router(market.router, prefix="/api/market")
app.include_router(analysis.router, prefix="/api/analysis")
app.include_router(sync.router, prefix="/api/sync")

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# 前端静态文件
static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
