from datetime import timedelta, datetime
from typing import Optional
from jose import jwt
import settings
from db.redis import get_redis_auth_pool


async def create_access_token(username: str, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": username}
    expire = datetime.now(settings.ekb_timezone) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    redis = await get_redis_auth_pool()
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expiration_datetime_str = expire.strftime("%Y-%m-%d %H:%M:%S")
    await redis.delete(f"user_token:{username}")
    await redis.hset(
        f"user_token:{username}",
        mapping={
            "token": encoded_jwt,
            "username": username,
            "expiration_datetime": expiration_datetime_str,
        },
    )
    await redis.expire(f"user_token:{username}", ttl)
    return encoded_jwt
