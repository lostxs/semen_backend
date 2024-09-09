from datetime import datetime
from typing import Union
from typing import cast
from typing import Optional
from uuid import UUID
from sqlalchemy import ColumnElement, select
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User
from db.models import ActivationCode
from db.models import ActivationStatus
import settings


###########################################################
# BLOCK FOR INTERACTION WITH DATABASE IN BUSINESS CONTEXT #
###########################################################


class UserDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(
        self, username: str, email: str, hashed_password: str
    ) -> User:
        new_user = User(username=username, email=email, hashed_password=hashed_password)
        self.db_session.add(new_user)
        await self.db_session.flush()
        return new_user

    @staticmethod
    async def activate_user(user: User, activation_time: datetime):
        user.is_active = True
        user.activation_time = activation_time

    async def get_user_by_email(self, email: str) -> Union[User, None]:
        query = select(User).filter(cast("ColumnElement[bool]", User.email == email))
        res = await self.db_session.execute(query)
        user_row = res.fetchone()
        if user_row is not None:
            return user_row[0]
        
    async def get_user_by_username(self, username: str) -> Union[User, None]:
        query = select(User).filter(cast("ColumnElement[bool]", User.username == username))
        res = await self.db_session.execute(query)
        user_row = res.fetchone()
        if user_row is not None:
            return user_row[0]

    async def get_user_by_id(self, user_id: UUID) -> Union[User, None]:
        query = select(User).filter(cast("ColumnElement[bool]", User.user_id == user_id))
        res = await self.db_session.execute(query)
        user_row = res.scalars().first()
        if user_row is not None:
            return user_row

    async def is_user_valid(self, user_id: UUID) -> bool:
        query = select(User).where(
            cast("ColumnElement[bool]", User.user_id == user_id)
        ).where(User.is_active)
        res = await self.db_session.execute(query)
        user = res.scalars().first()
        return user is not None


class ActivationCodeDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_activation_code(self, user_id: UUID, code: str) -> ActivationCode:
        activation_record = ActivationCode(
            user_id=user_id,
            code=code,
            created_at=datetime.now(settings.ekb_timezone),
            status=ActivationStatus.PENDING
        )
        self.db_session.add(activation_record)
        await self.db_session.flush()  
        return activation_record
    
    async def delete_activation_code(self, activation_record: ActivationCode):
        await self.db_session.delete(activation_record)
        await self.db_session.commit()

    
    async def find_activation_code(self, code: str) -> Optional[ActivationCode]:
        query = select(ActivationCode).where(ActivationCode.code == code)
        res = await self.db_session.execute(query)
        return res.scalars().first()

    async def update_activation_status(self, activation_record: ActivationCode, status: ActivationStatus):
        activation_record.status = status
        await self.db_session.commit()

