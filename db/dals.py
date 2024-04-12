from typing import Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User

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

    async def get_user_by_id(self, user_id: UUID) -> Union[User, None]:
        query = select(User).where(User.id == user_id)
        res = await self.db_session.execute(query)
        user_row = res.fetchone()
        if user_row is not None:
            return user_row[0]

    async def get_user_by_email(self, email: str) -> Union[User, None]:
        query = select(User).where(User.email == email)
        res = await self.db_session.execute(query)
        user_row = res.fetchone()
        if user_row is not None:
            return user_row[0]
