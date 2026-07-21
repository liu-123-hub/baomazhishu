"""API 路由聚合。"""
from fastapi import APIRouter

from . import dashboard, system

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["大屏数据"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])
