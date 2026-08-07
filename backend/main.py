"""后端服务启动入口。"""
import uvicorn
from app.config import settings

# --- Uvicorn 日志配置：统一格式，与 app.main._configure_logging() 保持一致 ---
# Uvicorn 默认使用自己的日志格式（无时间戳、无模块名），导致 backend.log 中
# 出现两种截然不同的日志行格式。此处通过 dictConfig 覆盖 Uvicorn 的 logger，
# 使所有日志行统一为 "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s" 格式。
UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        # Uvicorn 内部日志（启动、重载等）
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        # Uvicorn 访问日志（HTTP 请求记录）
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        # Uvicorn 错误日志
        "uvicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        # 降低 httpx 的 HEAD 请求日志级别，减少噪音
        "httpx": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_config=UVICORN_LOG_CONFIG,
    )
