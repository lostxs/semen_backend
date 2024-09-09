import asyncio
import logging
import settings
from datetime import timedelta
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi import Response
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from db.redis import get_redis_auth_pool
from redis.asyncio import Redis
from db.session import get_db
from logger import log_connection
from .actions import _get_user_by_username_for_auth, authenticate_user
from .actions import _get_user_by_email_for_auth
from .dependencies import maintain_session, verify_token
from .dependencies import get_cookie_or_token
from .dependencies import check_session
from .security import create_access_token

auth_router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@auth_router.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    logger.info("Attempting to authenticate user: username={}".format(form_data.username))
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        user_inactive = await _get_user_by_username_for_auth(form_data.username, db)
        if user_inactive and not user_inactive.is_active:
            logger.info("Inactive user tried to log in: username={}".format(form_data.username))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт не активирован. Пожалуйста, активируйте аккаунт.",
            )
        else:
            logger.info("Failed login attempt: username={}".format(form_data.username))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неправильное имя пользователя или пароль.",
            )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    session = await create_access_token(
        user_id=user.user_id,
        expires_delta=access_token_expires,
    )
    response.set_cookie(
        key="session",
        value=session,
        httponly=False,
        secure=False,
        samesite="lax"
    )
    return {"message": "Успешная авторизация"}


@auth_router.post("/logout")
async def logout(response: Response, request: Request, redis: Redis = Depends(get_redis_auth_pool)):
    user_id = await verify_token(request, redis)
    if user_id:
        await redis.delete(f"user_id:{user_id}")
    response.delete_cookie("access_token")
    return {"message": "Вы вышли из аккаунта"}


@auth_router.get("/verify")
async def protected_route(request: Request, redis: Redis = Depends(get_redis_auth_pool)):
    await verify_token(request, redis)
    return True


@auth_router.websocket("/ws")
async def websocket_endpoint(
        *,
        websocket: WebSocket,
        cookie_or_token: str = Depends(get_cookie_or_token),
        redis_auth: Redis = Depends(get_redis_auth_pool)
):
    await websocket.accept()
    user_id, token_valid = await check_session(cookie_or_token, redis_auth)
    if not token_valid:
        logger.info("Invalid or expired token for WebSocket: token={}".format(cookie_or_token))
        await websocket.close(code=4001, reason="Недействительный токен")
        return

    await websocket.send_json({"type": "AUTH_STATUS", "isAuthenticated": True})
    log_connection(websocket, endpoint="auth", user_id=str(user_id), action="connected")
    session_task = asyncio.create_task(maintain_session(websocket, cookie_or_token, redis_auth))

    try:
        while True:
            await websocket.receive_text()
            _, token_valid = await check_session(cookie_or_token, redis_auth)
            if not token_valid:
                await websocket.close(code=4001, reason="Токен устарел")
                break

            await websocket.send_json({"type": "message", "message": "Session is active"})
    except WebSocketDisconnect:
        log_connection(websocket, endpoint="auth", user_id=str(user_id), action="disconnected")
        session_task.cancel()
