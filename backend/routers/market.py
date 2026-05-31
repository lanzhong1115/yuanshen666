"""市场行情 API"""

from fastapi import APIRouter, HTTPException
from database import get_db
from services.market_data import (
    get_index_quotes,
    get_sector_quotes,
    get_sector_flow,
)

router = APIRouter()


@router.get("/indices")
async def market_indices():
    """获取大盘指数实时行情"""
    try:
        indices = get_index_quotes()
        return {"indices": indices, "updated_at": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def market_sectors(sort_by: str = "change_pct"):
    """获取行业板块行情"""
    try:
        sectors = get_sector_quotes(sort_by=sort_by)
        return {"sectors": sectors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/flow")
async def market_sector_flow():
    """获取板块资金流向"""
    try:
        flow_data = get_sector_flow()
        return {"flow": flow_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
