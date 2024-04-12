import json
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket
from typing import Dict

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions.message import get_messages, save_message
from db.models import ConnectionHistory


@dataclass
class ConnectionManager:
    active_connections: Dict[WebSocket, dict] = field(default_factory=dict)
    last_message_index: Dict[WebSocket, int] = field(default_factory=dict)

    async def connect(
        self,
        websocket: WebSocket,
        user: dict,
        db: AsyncSession,
        redis_pool_messages: Redis,
    ):
        await websocket.accept()
        self.active_connections[websocket] = user
        self.last_message_index[websocket] = -20

        initial_messages = await get_messages(redis_pool_messages, start=-20, count=20)
        await websocket.send_text(
            json.dumps({"type": "initial_load", "messages": initial_messages})
        )
        print(f"User {user.username} connected. Current messages: {initial_messages}")

        new_connection = ConnectionHistory(user_id=user.user_id)
        db.add(new_connection)
        await db.commit()
        await self.send_active_users()

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
        await websocket.send_text(json.dumps(message_data, ensure_ascii=False))
        await save_message(
            user_id=user.user_id,
            username=user.username,
            content=message,
            db=db,
            redis_pool_messages=redis_pool_messages,
        )

    async def broadcast(
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
        for connection in self.active_connections:
            if connection != sender_websocket:
                await connection.send_text(json.dumps(message_data, ensure_ascii=False))

    async def send_active_users(self):
        active_users = [user.username for user in self.active_connections.values()]
        users_list = json.dumps({"type": "users_list", "users": active_users})
        for websocket in self.active_connections:
            await websocket.send_text(users_list)


# def sanitize(text):
#    return html.escape(text)


#################################################################################
# Для полной истории
# async def connect(self, websocket: WebSocket, user: dict, db: AsyncSession):
#        await websocket.accept()
#        self.active_connections[websocket] = user
#        new_connection = ConnectionHistory(user_id=user.user_id)
#        if ConnectionHistory(user.user_id == user.user_id):
#        db.add(new_connection)
#        await db.commit()
#################################################################################
