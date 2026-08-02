"""WebSocket 连接管理。"""
import asyncio
import logging
from datetime import datetime
from typing import Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_CONNECTIONS = 50


class ConnectionManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        if len(self.active_connections) >= MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="服务器连接数已满")
            logger.warning(f"WebSocket 连接被拒绝（已达上限 {MAX_CONNECTIONS}）")
            return False
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")
        return True

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket 发送消息失败，标记断开: {e}")
                disconnected.add(connection)

        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_data(self, msg_type: str, data: Any):
        message = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"WebSocket 发送个人消息失败: {e}")
            await self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
