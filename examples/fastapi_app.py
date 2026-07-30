"""示例 1：FastAPI 应用接入 mini_logger

演示：
- 1 行 init 完成初始化
- 中间件注入 trace_id / user_id / client_ip
- 业务函数直接调用 mini_logger.info / error，无需手动传递上下文
- 异常自动捕获完整栈
- 敏感字段自动脱敏
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import mini_logger


def create_app() -> FastAPI:
    """构造 FastAPI 应用，集成 mini_logger。"""
    # === 1 行初始化 ===
    mini_logger.init(
        service="api-server",
        level="INFO",
        console=True,
        file=True,
        log_dir="logs/api",
        json_console=False,  # 控制台人类可读；文件始终 JSON
    )

    app = FastAPI(title="mini_logger FastAPI demo")

    # === 中间件：每个请求注入链路上下文 ===
    @app.middleware("http")
    async def log_context_middleware(request: Request, call_next):
        # 优先从上游 X-Trace-Id 继承，没有则生成
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        user_id = request.headers.get("X-User-Id", "")
        client_ip = request.client.host if request.client else ""

        token = mini_logger.bind_context(
            trace_id=trace_id,
            request_id=uuid.uuid4().hex[:16],
            user_id=user_id,
            client_ip=client_ip,
        )
        try:
            mini_logger.info(
                "request start",
                method=request.method,
                path=request.url.path,
            )
            response = await call_next(request)
            mini_logger.info(
                "request end",
                status=response.status_code,
            )
            # 把 trace_id 回写响应头，便于前端排错
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            token.reset()
            mini_logger.clear_context()

    # === 业务路由 ===
    @app.get("/api/users/{user_id}")
    async def get_user(user_id: str):
        # 业务日志自动携带 trace_id / user_id / client_ip
        mini_logger.info("fetch user", user_id=user_id, action="get_user")
        # 模拟数据库查询
        if user_id == "missing":
            try:
                raise ValueError(f"user {user_id} not found")
            except ValueError as e:
                # 异常栈会被完整记录，无需手动 traceback
                mini_logger.error("user lookup failed", exc=e, user_id=user_id)
                return JSONResponse(
                    status_code=404,
                    content={"error": "not_found", "trace_id": mini_logger.get_logger().level.name},
                )
        # 假装查询出来的敏感字段：会被自动脱敏
        mini_logger.info(
            "user fetched",
            user_id=user_id,
            phone="13812345678",       # 自动遮蔽
            id_card="110101199003078888",  # 自动遮蔽
            password="s3cret",          # 自动 *** 
        )
        return {"user_id": user_id, "name": "Alice"}

    @app.get("/api/health")
    async def health():
        mini_logger.debug("health check")  # 默认 INFO 级别，DEBUG 不输出
        return {"status": "ok"}

    return app


# 运行：uvicorn examples.fastapi_app:app --reload
app = create_app()


if __name__ == "__main__":
    # 直接运行会创建 app 但需要 uvicorn 启动 HTTP 服务
    # 这里仅做日志演示
    import uvicorn

    mini_logger.info("starting api server", port=8000)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    mini_logger.shutdown()
