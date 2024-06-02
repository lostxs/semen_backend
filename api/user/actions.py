import logging
import settings
from typing import Union
from datetime import datetime
from datetime import timedelta
from uuid import UUID
from db.models import ActivationStatus, User
from db.models import ActivationCode
from hashing import Hasher
from apscheduler.triggers.date import DateTrigger
from scheduler.session import async_session_factory
from scheduler.tasks import scheduler
from scheduler.tasks import retrieve_job_id
from scheduler.tasks import store_job_id
from scheduler.tasks import remove_job_id
from scheduler.tasks import expire_activation_code
from api.schemas import UserCreate
from api.schemas import ShowUser
from smtp.activate_account import generate_activation_code
from smtp.activate_account import send_activation_code
from .dals import UserDAL
from .dals import ActivationCodeDAL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def _create_new_user(body: UserCreate, session) -> ShowUser:
    try:
        async with session.begin():
            user_dal = UserDAL(session)
            user = await user_dal.create_user(
                username=body.username,
                email=body.email,
                hashed_password=Hasher.get_password_hash(body.password),
            )
            await session.flush()
            activation_code = await generate_activation_code(session)
            expiration_time = datetime.now(settings.ekb_timezone) + timedelta(
                minutes=settings.ACTIVATION_CODE_EXPIRE_MINUTES)
            activation_record = ActivationCode(
                user_id=user.user_id,
                code=activation_code,
                created_at=datetime.now(settings.ekb_timezone),
            )
            session.add(activation_record)
            await session.commit()
            await send_activation_code(user.email, activation_code)

            job = scheduler.add_job(
                expire_activation_code,
                trigger=DateTrigger(run_date=expiration_time),
                args=[activation_record.id, async_session_factory],
                id=f"user_{user.user_id}_activation",
                misfire_grace_time=300
            )
            logging.info(f"Scheduled expiration job for user {user.user_id} with job ID {job.id}")
            await store_job_id(user.user_id, job.id)

            return ShowUser(
                # user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
            )
    except Exception:
        await session.rollback()
        raise


async def _activate_user_account(user_id: UUID, code: str, session):
    user_dal = UserDAL(session)
    activation_dal = ActivationCodeDAL(session)
    now = datetime.now(settings.ekb_timezone)

    try:
        async with session.begin():
            activation_record = await activation_dal.create_activation_code(user_id, code)
            if not activation_record or activation_record.status == ActivationStatus.ACTIVATED:
                raise ValueError("Invalid or already used activation code.")

            if now - activation_record.created_at > timedelta(minutes=settings.ACTIVATION_CODE_EXPIRE_MINUTES):
                await activation_dal.update_activation_status(activation_record, ActivationStatus.EXPIRED)
                raise ValueError("Activation code expired")

            user = await user_dal.get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User not found")

            await user_dal.activate_user(user, now)
            await activation_dal.update_activation_status(activation_record, ActivationStatus.ACTIVATED)

            job_id = await retrieve_job_id(user_id)
            if job_id:
                scheduler.remove_job(job_id)
                await remove_job_id(user_id)
                logging.info(f"Cancelled job {job_id} for user {user_id} upon successful activation")
    except Exception:
        await session.rollback()
        raise


async def _get_user_by_id(user_id, session) -> Union[User, None]:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_user_by_id(
            user_id=user_id
        )
        if user is not None:
            return user
