from datetime import datetime, timedelta
from typing import Union
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import UserCreate, ShowUser
from db.dals import UserDAL
from db.models import User, ActivationCode
from hashing import Hasher
from settings import ACTIVATION_CODE_EXPIRE_MINUTES, ekb_timezone
from smtp.activate_account import generate_activation_code, send_activation_code


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
            activation_record = ActivationCode(
                user_id=user.user_id,
                code=activation_code,
                created_at=datetime.now(ekb_timezone),
            )
            session.add(activation_record)
            await session.commit()
            await send_activation_code(user.email, activation_code)
            return ShowUser(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
            )
    except Exception:
        await session.rollback()
        raise


async def _get_user_by_id(user_id, session) -> Union[User, None]:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_user_by_id(user_id=user_id)
        if user is not None:
            return user


async def _activate_user_account(user_id: UUID, code: str, db: AsyncSession):
    try:
        async with db.begin():
            activation_record = await db.execute(
                select(ActivationCode).where(
                    and_(ActivationCode.user_id == user_id, ActivationCode.code == code)
                )
            )
            activation_record = activation_record.scalars().first()
            if not activation_record:
                raise ValueError("Invalid activation code")
            if datetime.now(ekb_timezone) - activation_record.created_at > timedelta(
                minutes=ACTIVATION_CODE_EXPIRE_MINUTES
            ):
                raise ValueError("Activation code expired")
            user = await db.execute(select(User).where(User.user_id == user_id))
            user = user.scalars().first()
            if not user:
                raise NoResultFound("User not found")
            user.is_active = True
            await db.delete(activation_record)
            await db.commit()
    except Exception:
        await db.rollback()
        raise
