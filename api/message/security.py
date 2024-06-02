import json
import settings
import jwt
from datetime import datetime
from datetime import timedelta
from typing import Optional
from uuid import UUID
from db.redis import get_redis_chat_auth_pool


async def create_chat_token(user_id: UUID, username: str, expires_delta: Optional[timedelta] = None):
    expire = datetime.now(settings.ekb_timezone) + (
            expires_delta or timedelta(minutes=settings.CHAT_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {
        "sub": str(user_id),
        "username": str(username),
        "exp": expire.timestamp()
        # "scope": "chat"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    redis = await get_redis_chat_auth_pool()
    ttl = settings.CHAT_TOKEN_EXPIRE_MINUTES * 60
    expiration_datetime_str = expire.strftime("%Y-%m-%d %H:%M:%S")
    user_key = f"chat_user_id:{user_id}"
    await redis.delete(user_key)
    await redis.setex(
        f"chat_user_id:{user_id}",
        ttl,
        json.dumps({
            "token": encoded_jwt,
            "user_id": str(user_id),
            "username": str(username),
            "exp": expiration_datetime_str
        })
    )

    return encoded_jwt
