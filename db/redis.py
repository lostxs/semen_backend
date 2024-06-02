from typing import Optional
from apscheduler.jobstores.redis import RedisJobStore
from redis.asyncio import Redis
from settings import REDIS_URL

redis_pool_auth: Optional[Redis] = None
redis_scheduler_pool: Optional[Redis] = None
redis_pool_chat_auth: Optional[Redis] = None
redis_pool_messages: Optional[Redis] = None


async def get_redis_auth_pool() -> Redis:
    return await Redis.from_url(
        REDIS_URL, encoding="utf-8", decode_responses=True, db=0
    )


async def get_redis_messages_pool() -> Redis:
    return await Redis.from_url(
        REDIS_URL, encoding="utf-8", decode_responses=True, db=1
    )


async def get_redis_chat_auth_pool() -> Redis:
    return await Redis.from_url(
        REDIS_URL, encoding="utf-8", decode_responses=True, db=2
    )


async def get_redis_scheduler_pool() -> Redis:
    return await Redis.from_url(
        REDIS_URL, encoding="utf-8", decode_responses=True, db=3
    )


scheduler = {
    'default': RedisJobStore(
        jobs_key='apscheduler.jobs', run_times_key='apscheduler.run_times', host='localhost', port=6379, db=3
    )
}






