import json
import logging
import settings
import jwt
from datetime import datetime
from typing import Tuple
from typing import Optional
from uuid import UUID
from redis.asyncio import Redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_chat_session(token: str, redis_auth: Redis) -> Tuple[Optional[UUID], bool]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if user_id is None:
            return None, False

        user_key = f"chat_user_id:{user_id}"
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
    except jwt.ExpiredSignatureError as e:
        logger.info(f"Token expired: {e}")
        return None, False
    except (jwt.PyJWTError, ValueError) as e:
        logger.info(f"Authentication error: {e}")
        return None, False
