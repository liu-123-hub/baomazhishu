"""FastAPI 主应用，实时数据大屏后端服务。"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import db
from .routers import api_router
from .websocket import manager
from .data_service import data_service
from .auto_collector import auto_collector


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_dir = os.path.join(settings.BACKEND_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


_configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动顺序：DB初始化→数据预热→WS广播→自动采集。"""
    print("=" * 65)
    print("   实时数据大屏系统 - FastAPI 后端")
    print(f"   {settings.PROJECT_NAME}")
    print("=" * 65)

    print("[1/4] 初始化数据库...")
    await db.init_database()
    print("   [OK] 数据库就绪")

    print("[2/4] 启动数据服务预热（后台执行）...")
    warmup_task = asyncio.create_task(_warmup_data_service())
    print("   [OK] 数据服务预热已在后台启动")

    print("[3/4] 启动实时数据推送...")
    broadcast_task = asyncio.create_task(broadcast_data_loop())
    print("   [OK] 实时推送已启动")

    print("[4/4] 启动自动数据采集（延迟5秒后首次执行）...")
    await auto_collector.start(delayed_start=True)
    print("   [OK] 自动采集已启动")

    print("\n" + "=" * 65)
    print("   [OK] 系统已启动")
    print(f"   API 服务: http://{settings.HOST}:{settings.PORT}")
    print(f"   API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 65 + "\n")

    yield

    print("\n[STOP] 正在关闭系统...")
    broadcast_task.cancel()
    warmup_task.cancel()
    await auto_collector.close()
    print("   [OK] 系统已关闭")


async def _warmup_data_service():
    try:
        await asyncio.sleep(0.5)
        await data_service.get_dashboard_overview()
        logger.info("数据服务预热完成")
    except Exception as e:
        logger.warning(f"数据服务预热异常（不影响使用）: {e}")


async def broadcast_data_loop():
    while True:
        try:
            if manager.connection_count > 0:
                overview = await data_service.get_dashboard_overview()
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

    cors_kwargs = {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.CORS_ALLOW_LOCALHOST_REGEX:
        cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1):\d+"
    app.add_middleware(CORSMiddleware, **cors_kwargs)

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

    _configure_static(app)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        connected = await manager.connect(websocket)
        if not connected:
            return
        try:
            try:
                overview = await data_service.get_dashboard_overview()
                await manager.send_personal_message(
                    {"type": "dashboard", "data": overview, "timestamp": datetime.now().isoformat()},
                    websocket,
                )
            except Exception as e:
                logger.warning(f"WebSocket 初始推送失败: {e}")

            while True:
                try:
                    msg = await websocket.receive_text()
                    if msg == "ping":
                        await manager.send_personal_message(
                            {"type": "pong"}, websocket
                        )
                except WebSocketDisconnect:
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"WebSocket 连接异常: {e}")
        finally:
            await manager.disconnect(websocket)

    return app


def _configure_static(app: FastAPI) -> None:
    """挂载前端静态资源并配置 SPA 路由回退。

    - 存在 STATIC_DIR（已构建前端）时：托管 /assets，根路径返回 index.html，
      其余未匹配路径回退到 index.html 以支持前端路由；/api/* 仍返回 JSON 404
    - 开发模式且未构建前端时：根路径返回服务信息 JSON
    """
    static_dir = settings.STATIC_DIR
    index_html = static_dir / "index.html" if static_dir else None

    if not (static_dir and static_dir.is_dir() and index_html and index_html.is_file()):
        @app.get("/", include_in_schema=False)
        async def root():
            return {
                "name": settings.PROJECT_NAME,
                "version": "1.0.0",
                "docs": "/docs",
                "api_prefix": settings.API_V1_PREFIX,
            }
        return

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    index_path = str(index_html)

    @app.get("/", include_in_schema=False)
    async def _spa_root():
        return FileResponse(index_path)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # /api 与 /ws 已由专用路由处理；落到此处且以 api/ 开头视为未知 API，返回 JSON 404
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(index_path)


app = create_app()
