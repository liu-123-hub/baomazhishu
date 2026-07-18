"""FastAPI 主应用，实时数据大屏后端服务。"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import db
from .routers import api_router
from .websocket import manager
from .data_service import data_service
from .auto_collector import auto_collector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    print("=" * 65)
    print("   🚀 实时数据大屏系统 - FastAPI 后端")
    print(f"   📅 {settings.PROJECT_NAME}")
    print("=" * 65)

    print("[1/4] 初始化数据库...")
    await db.init_database()
    print("   ✅ 数据库就绪")

    print("[2/4] 初始化数据服务...")
    _ = await data_service.get_dashboard_overview()
    print("   ✅ 数据服务就绪")

    print("[3/4] 启动实时数据推送...")
    broadcast_task = asyncio.create_task(broadcast_data_loop())
    print("   ✅ 实时推送已启动")

    print("[4/4] 启动自动数据采集...")
    await auto_collector.start()
    print("   ✅ 自动采集已启动")

    print("\n" + "=" * 65)
    print(f"   ✅ 系统已启动")
    print(f"   🌐 API 服务: http://{settings.HOST}:{settings.PORT}")
    print(f"   📡 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"   🔌 WebSocket: ws://{settings.HOST}:{settings.PORT}/api/v1/ws-test/ws")
    print("=" * 65 + "\n")

    yield

    print("\n⏹️  正在关闭系统...")
    broadcast_task.cancel()
    await auto_collector.close()
    print("   ✅ 系统已关闭")


async def broadcast_data_loop():
    try:
        while True:
            if manager.connection_count > 0:
                overview = await data_service._compute_dashboard_overview()
                await manager.broadcast_data("dashboard", overview)
            await asyncio.sleep(settings.WS_BROADCAST_INTERVAL)
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="实时数据大屏系统 API 文档",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api_prefix": settings.API_V1_PREFIX,
        }

    return app


app = create_app()
