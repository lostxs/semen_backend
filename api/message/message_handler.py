from fastapi import APIRouter, Query
from fastapi import HTTPException
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import Depends
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from websocket.action import handle_websocket_connect
from websocket.action import handle_messages
from websocket.action import handle_websocket_disconnect
from db.session import get_db
from db.redis import get_redis_chat_auth_pool
from db.redis import get_redis_messages_pool
from .dependencies import check_chat_session
from .security import create_chat_token
from ..user.actions import _get_user_by_id # noqa
from ..user.dependencies import get_current_user
from logger import log_connection

message_router = APIRouter()


@message_router.get("/request-chat-token")
async def get_chat_token(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or not authenticated")
    chat_token = await create_chat_token(user.user_id, user.username)
    return JSONResponse({"chat_token": chat_token})


@message_router.websocket("/ws")
async def websocket_endpoint(
        *,
        websocket: WebSocket,
        token: str = Query(default=None, alias="chat_token"),
        redis_auth: Redis = Depends(get_redis_chat_auth_pool),
        redis_messages: Redis = Depends(get_redis_messages_pool),
        session: AsyncSession = Depends(get_db)
):
    user = None
    if token is None:
        await websocket.close(code=4001, reason="No token provided")
        return

    user_id, token_valid = await check_chat_session(token, redis_auth)
    if not token_valid:
        await websocket.close(code=4001, reason="No token valid")
        return

    try:
        while True:
            user = await _get_user_by_id(session=session, user_id=user_id)
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            if not token_valid:
                await websocket.close(code=4001, reason="Token expired")
                break

            await handle_websocket_connect(user, websocket, session, redis_messages)
            log_connection(websocket, endpoint="messages", user_id=str(user_id), action="connected")
            await handle_messages(websocket, user, session, redis_messages)
    except WebSocketDisconnect:
        log_connection(websocket, endpoint="messages", user_id=str(user_id), action="disconnected")
        await handle_websocket_disconnect(user, websocket, session)
