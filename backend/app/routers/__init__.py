"""API 路由聚合。"""
from fastapi import APIRouter

from . import dashboard, system, ws_test

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["大屏数据"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])
api_router.include_router(ws_test.router, prefix="/ws-test", tags=["WebSocket测试"])
