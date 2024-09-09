import json
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import UUID
from fastapi import WebSocket
from typing import Dict
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from api.message.actions import get_messages
from api.message.actions import save_message
from db.models import ConnectionHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class User:
    user_id: UUID
    username: str


@dataclass
class ConnectionManager:
    active_connections: Dict[WebSocket, User] = field(default_factory=dict)
    last_message_index: Dict[WebSocket, int] = field(default_factory=dict)

    async def connect(
        self,
        websocket: WebSocket,
        user: User,
        db: AsyncSession,
        redis_pool_messages: Redis,
    ):
        await websocket.accept()
        self.active_connections[websocket] = user
        self.last_message_index[websocket] = -20

        initial_messages = await get_messages(redis_pool_messages, start=-20, count=20)
        sanitized_messages = [
            {
                "id": message["id"],
                "username": message["username"],
                "content": message["content"],
                "created_at": message["created_at"]
            }
            for message in initial_messages
        ]
        await websocket.send_text(
            json.dumps({"type": "initial_load", "messages": sanitized_messages})
        )

        new_connection = ConnectionHistory(user_id=user.user_id)
        db.add(new_connection)
        await db.commit()
        await self.send_active_users()

    async def send_active_users(self):
        active_users = [user.username for user in self.active_connections.values()]
        users_list = json.dumps({"type": "users_list", "users": active_users})
        for websocket in self.active_connections:
            if not websocket.client_state == WebSocketState.DISCONNECTED:
                await websocket.send_text(users_list)

    async def disconnect(self, websocket: WebSocket, db: AsyncSession):
        user = self.active_connections.pop(websocket, None)
        self.last_message_index.pop(websocket, None)
        if user:
            last_connection = await db.execute(
                select(ConnectionHistory)
                .filter_by(user_id=user.user_id, disconnected_at=None)
                .order_by(ConnectionHistory.connected_at.desc())
                .limit(1)
            )
            last_connection = last_connection.scalars().first()
            if last_connection:
                last_connection.disconnected_at = datetime.now()
        await db.commit()
        await self.send_active_users()

    async def send_personal_message(
        self,
        message: str,
        websocket: WebSocket,
        db: AsyncSession,
        redis_pool_messages: Redis,
    ):
        user = self.active_connections[websocket]
        message_data = {
            "username": user.username,
            "content": message,
            "created_at": datetime.now().isoformat(),
            "type": "new_message",
        }
        logger.info(f"Sending message: {message_data}")
        await websocket.send_text(json.dumps(message_data, ensure_ascii=False))
        await save_message(
            user_id=str(user.user_id),
            username=user.username,
            content=message,
            db=db,
            redis_pool_messages=redis_pool_messages,
        )

    async def broadcast_message(
        self,
        message: str,
        username: str,
        sender_websocket: WebSocket,
        system_message: bool = False,
    ):
        message_type = "system_message" if system_message else "broadcast_message"
        message_data = {
            "username": "system" if system_message else username,
            "content": message,
            "created_at": datetime.now().isoformat(),
            "type": message_type,
        }
        logger.info(f"Broadcasting message: {message_data}")
        for connection in self.active_connections:
            if connection != sender_websocket:
                await connection.send_text(json.dumps(message_data, ensure_ascii=False))

    async def broadcast_typing(self, username: str, sender_websocket: WebSocket):
        typing_data = json.dumps({"type": "typing", "username": username})
        for connection in self.active_connections:
            if connection != sender_websocket and connection.client_state == WebSocketState.CONNECTED:
                await connection.send_text(typing_data)

    async def broadcast_stop_typing(self, username: str, sender_websocket: WebSocket):
        stop_typing_data = json.dumps({"type": "stop_typing", "username": username})
        for connection in self.active_connections:
            if connection != sender_websocket and connection.client_state == WebSocketState.CONNECTED:
                await connection.send_text(stop_typing_data)
