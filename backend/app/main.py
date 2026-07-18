"""FastAPI 主应用，实时数据大屏后端服务。"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import settings
from .database import db
from .routers import api_router
from .websocket import manager
from .data_service import data_service
from .auto_collector import auto_collector

logger = logging.getLogger(__name__)


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
    """定时广播大盘概览到所有 WebSocket 连接。
    任何单次异常（DB 锁、JSON 解析失败等）都被捕获并记录，
    避免推送循环静默停止导致前端不再收到更新。
    """
    while True:
        try:
            if manager.connection_count > 0:
                overview = await data_service._compute_dashboard_overview()
                await manager.broadcast_data("dashboard", overview)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"广播数据循环异常，将在下个周期重试: {e}")
        try:
            await asyncio.sleep(settings.WS_BROADCAST_INTERVAL)
        except asyncio.CancelledError:
            raise


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

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err.get("loc", [])) if err.get("loc") else "unknown"
            errors.append({"field": field, "message": err.get("msg", "参数验证失败")})
        logger.warning(f"请求参数验证失败: {request.url.path} - {errors}")
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数验证失败",
                "data": None,
                "errors": errors
            }
        )

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": f"请求的资源不存在: {request.url.path}",
                "data": None
            }
        )

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc):
        logger.error(f"服务器内部错误: {request.url.path}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "data": None
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理的异常: {request.url.path} - {str(exc)}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "data": None
            }
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
