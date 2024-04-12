from typing import Union

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from redis.asyncio import Redis

from db.dals import UserDAL
from db.models import User
from db.redis import get_redis_auth_pool
from hashing import Hasher
from settings import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")


async def _get_user_by_email_for_auth(email: str, session: AsyncSession):
    async with session.begin():
        user_dal = UserDAL(session)
        return await user_dal.get_user_by_email(email=email)


async def authenticate_user(
    email: str, password: str, db: AsyncSession
) -> Union[User, None]:
    user = await _get_user_by_email_for_auth(email=email, session=db)
    if user is None or not user.is_active:
        return
    if not Hasher.verify_password(password, user.hashed_password):
        return
    return user


async def verify_user_token(
    request: Request, redis: Redis = Depends(get_redis_auth_pool)
) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None or not await redis.hgetall(f"user_token:{user_email}"):
            raise HTTPException(
                status_code=401, detail="Authentication failed or token expired"
            )
        return user_email
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )


async def get_user_details_by_username(db: AsyncSession, username: str) -> User:
    query = select(User).filter(User.username == username)
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user
