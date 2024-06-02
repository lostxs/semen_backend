import jwt
import settings
from fastapi import Depends
from fastapi import Cookie
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from db.redis import get_redis_auth_pool
from db.session import get_db
from .actions import _get_user_by_id


async def get_current_user(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis_auth_pool),
        token: str = Cookie(default=None, alias="session")
):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        session_active = await redis.exists(f"user_id:{user_id}")
        if not session_active:
            raise HTTPException(status_code=401, detail="Session has been revoked")

        user = await _get_user_by_id(session=session, user_id=user_id)
        if user is None:
            raise credentials_exception

        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")
