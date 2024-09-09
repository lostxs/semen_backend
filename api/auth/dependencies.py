import asyncio
import json
import logging
import settings
import jwt
from jwt import ExpiredSignatureError
from datetime import datetime
from typing import Tuple
from typing import Union
from typing import Optional
from uuid import UUID
from fastapi import Depends
from fastapi import Cookie
from fastapi import Query
from fastapi import HTTPException
from fastapi import status
from fastapi import Request
from fastapi import WebSocketException
from starlette.websockets import WebSocketState
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from db.redis import get_redis_auth_pool

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_token(
    request: Request, redis: Redis = Depends(get_redis_auth_pool)
) -> UUID:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Необходима авторизация.")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if user_id is None or not await redis.get(f"user_id:{user_id}"):
            raise HTTPException(
                status_code=401, detail="Авторизация не удалась. Пожалуйста, авторизуйтесь заново."
            )
        return user_id
    except ExpiredSignatureError:
        logger.info("Token has expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен истек. Пожалуйста, авторизуйтесь заново.")
    except (jwt.PyJWTError, ValueError) as e:
        logger.info(f"Authentication error: {e}")
        raise HTTPException(
            status_code=401, detail="Необходима авторизация. Пожалуйста, авторизуйтесь заново."
        )


async def check_session(token: str, redis_auth: Redis) -> Tuple[Optional[UUID], bool]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if user_id is None:
            return None, False

        user_key = f"user_id:{user_id}"
        session_data = await redis_auth.get(user_key)
        if session_data is None:
            return None, False

        session_info = json.loads(session_data)
        expiration_time_str = session_info['exp']
        expiration_time = datetime.strptime(expiration_time_str, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=settings.ekb_timezone)
        current_time = datetime.now(settings.ekb_timezone)

        if current_time > expiration_time:
            await redis_auth.delete(user_key)
            return None, False
        return user_id, True
    except (jwt.PyJWTError, ValueError) as e:
        logger.info(f"Authentication error: {e}")
        return None, False


async def maintain_session(websocket, token, redis_auth):
    try:
        while True:
            await asyncio.sleep(10)  # 10 seconds
            _, token_valid = await check_session(token, redis_auth)
            if not token_valid:
                await websocket.send_json({"type": "AUTH_STATUS", "isAuthenticated": False})
                if websocket.application_state != WebSocketState.DISCONNECTED:
                    await websocket.close(code=4001, reason="Connections refused.")
                    break
    except Exception as e:
        logger.error("Error in maintain_session: %s", e)


async def get_cookie_or_token(
    session: Union[str, None] = Cookie(default=None),
    token: Union[str, None] = Query(default=None),
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token
