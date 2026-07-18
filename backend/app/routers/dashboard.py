"""仪表盘路由。"""
from fastapi import APIRouter, Query
from app.data_service import (
    get_dashboard_overview,
    get_sector_detail,
    get_line_chart_data
)

router = APIRouter()


@router.get("/overview")
async def dashboard_overview():
    return await get_dashboard_overview()


@router.get("/sector-detail")
async def sector_detail(
    code: str = Query(..., description="板块代码")
):
    return await get_sector_detail(code)


@router.get("/line-chart")
async def line_chart_data(
    sectors: str = Query("", description="板块代码列表，逗号分隔"),
    days: int = Query(7, ge=1, le=365, description="天数范围")
):
    return await get_line_chart_data(sectors, days)


@router.get("/history")
async def history_trend(
    code: str = Query(None, description="板块代码，为空则返回所有"),
    days: int = Query(7, ge=1, le=365, description="天数范围")
):
    from app.data_service import get_history_trend
    return await get_history_trend(code, days)


@router.get("/market-data")
async def market_data(
    sector: str = Query(None, description="板块代码，为空则返回所有")
):
    from app.data_service import get_market_data
    return await get_market_data(sector)


@router.get("/etf-correlation")
async def etf_correlation(
    sector: str = Query(..., description="板块代码"),
    days: int = Query(30, ge=3, le=365, description="计算天数")
):
    from app.data_service import get_etf_correlation
    return await get_etf_correlation(sector, days)


@router.get("/capital-flow")
async def capital_flow_summary():
    from app.data_service import get_capital_flow_summary
    return await get_capital_flow_summary()


@router.get("/capital-flow/detail")
async def capital_flow_detail(
    type: str = Query(..., description="数据类型: limit_up 或 dragon_tiger"),
    date: str = Query(None, description="交易日 YYYY-MM-DD，为空返回最新")
):
    from app.data_service import get_capital_flow_detail
    return await get_capital_flow_detail(type, date)