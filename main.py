import asyncio
import logging
import uvicorn
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from starlette_exporter import PrometheusMiddleware, handle_metrics

from api.actions.auth import get_user_details_by_username
from api.handlers import user_router, verify_user_token
from api.login_handler import login_router

from db.redis import get_redis_auth_pool, get_redis_messages_pool
from db.session import get_db
from websocket.action import handle_messages, handle_websocket_disconnect, manager


app = FastAPI()
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

main_api_router = APIRouter()
main_api_router.include_router(user_router, prefix="/user", tags=["user"])
main_api_router.include_router(login_router, prefix="/login", tags=["login"])
app.include_router(main_api_router)


@app.get("/metrics")
async def handle_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/{username}")
async def websocket_endpoint(
    websocket: WebSocket,
    username: str,
    redis_auth: Redis = Depends(get_redis_auth_pool),
    redis_messages: Redis = Depends(get_redis_messages_pool),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await verify_user_token(websocket, redis_auth)
        if not user or user != username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = await get_user_details_by_username(db, username)
        await manager.connect(websocket, user, db, redis_messages)
        join_message = f"Client #{user.username} joined the chat."
        await manager.broadcast(
            join_message, user.username, websocket, system_message=True
        )

        await handle_messages(websocket, user, db, redis_messages)

    except WebSocketDisconnect:
        await handle_websocket_disconnect(user, websocket, db)
    except Exception as e:
        logging.error(f"error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@app.websocket("/ws/auth/")
async def auth(
    websocket: WebSocket,
    redis_auth: Redis = Depends(get_redis_auth_pool),
):
    try:
        user = await verify_user_token(websocket, redis_auth)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        while True:
            try:
                await websocket.receive_text()
                if not await verify_user_token(websocket, redis_auth):
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logging.error(f"Session check error: {e}")
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                break
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await websocket.close()


@app.on_event("startup")
async def startup_event():
    await get_redis_auth_pool()
    await get_redis_messages_pool()


@app.on_event("shutdown")
async def shutdown_event():
    redis_pool = await get_redis_auth_pool()
    redis_pool_message = await get_redis_messages_pool()
    await redis_pool_message.close()
    await redis_pool.close()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
    )
