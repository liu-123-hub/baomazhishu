from fastapi import APIRouter, Query
from app.data_service import (
    get_dashboard_overview,
    get_sector_detail,
    get_line_chart_data
)
from app.config import settings

router = APIRouter()


@router.get("/version")
async def sector_version():
    from analyzer.index_calculator import get_version_info
    return {
        "code": 200,
        "data": get_version_info()
    }


@router.get("/config")
async def sector_config():
    from analyzer.index_calculator import SECTOR_NAMES, SECTOR_META, SECTOR_CATEGORIES, TIER_COLORS, INDUSTRY_SECTORS, CONCEPT_SECTORS
    return {
        "code": 200,
        "data": {
            "sector_names": SECTOR_NAMES,
            "sector_meta": SECTOR_META,
            "sector_categories": SECTOR_CATEGORIES,
            "tier_colors": TIER_COLORS,
            "industry_sectors": INDUSTRY_SECTORS,
            "concept_sectors": CONCEPT_SECTORS,
        }
    }


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


@router.get("/index-ratio")
async def index_ratio_data(
    unit: str = Query("month", description="时间聚合单位: year/quarter/month")
):
    """获取创业板指/中证红利比值面积图数据。"""
    from app.data_service import get_index_ratio_data
    return await get_index_ratio_data(unit)


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
