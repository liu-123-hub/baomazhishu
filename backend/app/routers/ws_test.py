"""WebSocket 测试路由。"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio

from ..websocket import manager
from ..data_service import data_service

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await manager.send_personal_message({
            "type": "hello",
            "data": {
                "message": "连接成功",
                "connection_count": manager.connection_count,
            },
            "timestamp": datetime.now().isoformat(),
        }, websocket)

        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1
                )
                await handle_client_message(websocket, data)
            except asyncio.TimeoutError:
                pass

            overview = await data_service._compute_dashboard_overview()
            await manager.send_personal_message({
                "type": "dashboard",
                "data": overview,
                "timestamp": datetime.now().isoformat(),
            }, websocket)

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: str):
    try:
        import json
        data = json.loads(message)
        msg_type = data.get("type", "")

        if msg_type == "ping":
            await manager.send_personal_message({
                "type": "pong",
                "data": {"timestamp": datetime.now().isoformat()},
            }, websocket)
        elif msg_type == "subscribe":
            channel = data.get("channel", "")
            await manager.send_personal_message({
                "type": "subscribed",
                "data": {"channel": channel},
                "timestamp": datetime.now().isoformat(),
            }, websocket)
    except Exception:
        pass
