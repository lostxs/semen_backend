import logging
from api.user.dals import ActivationCodeDAL
import settings
from datetime import timedelta
from uuid import UUID
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from db.models import ActivationCode
from db.models import ActivationStatus
from db.redis import scheduler
from db.redis import get_redis_scheduler_pool

scheduler = AsyncIOScheduler(jobstores=scheduler, job_defaults={'misfire_grace_time': 300})

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def expire_activation_code(activation_code_id, session_factory):
    async with session_factory() as session:
        activation_dal = ActivationCodeDAL(session)

        result = await session.execute(
            select(ActivationCode)
            .where(ActivationCode.id == activation_code_id)
        )
        activation_code = result.scalars().first()

        if activation_code.status == ActivationStatus.PENDING:
            await activation_dal.delete_activation_code(activation_code)
            logging.info(f"Expired and deleted activation code for user ID {activation_code.id}")

            job_id = await retrieve_job_id(activation_code.id)
            if job_id:
                job = scheduler.get_job(job_id)  
                if job:
                    scheduler.remove_job(job_id)
                    logging.info(f"Removed job {job_id} for expired activation {activation_code.id}")
                else:
                    logging.warning(f"Job {job_id} not found, possibly already removed.")
                
                await remove_job_id(activation_code.id)
        else:
            logging.info(
                f"No action needed: Activation code status for user ID {activation_code.id} "
                f"is already {activation_code.status}"
            )


async def store_job_id(user_id: UUID, job_id: str):
    redis = await get_redis_scheduler_pool()
    key = f"user:{user_id}:job"
    await redis.set(key, job_id)
    expiry_seconds = timedelta(hours=1).total_seconds()
    await redis.expire(key, time=int(expiry_seconds))


async def retrieve_job_id(user_id: UUID) -> str:
    redis = await get_redis_scheduler_pool()
    key = f"user:{user_id}:job"
    job_id = await redis.get(key)
    if job_id is None:
        logging.warning(f"Job ID for user {user_id} not found or expired.")
    return job_id


async def remove_job_id(user_id: UUID):
    redis = await get_redis_scheduler_pool()
    key = f"user:{user_id}:job"
    await redis.delete(key)


async def refresh_job_id(user_id: UUID):
    redis = await get_redis_scheduler_pool()
    key = f"user:{user_id}:job"
    job_id = await redis.get(key)
    if job_id:
        expiry_seconds = timedelta(minutes=settings.ACTIVATION_CODE_EXPIRE_MINUTES).total_seconds()
        await redis.expire(key, time=int(expiry_seconds))
        logging.info(f"Refreshed job ID for user {user_id}")
