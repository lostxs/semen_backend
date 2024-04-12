from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from api.actions.auth import (
    authenticate_user,
    _get_user_by_email_for_auth,
    verify_user_token,
)
from db.session import get_db
from security import create_access_token

login_router = APIRouter()


@login_router.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        user_inactive = await _get_user_by_email_for_auth(form_data.username, db)
        if user_inactive and not user_inactive.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not activated, please activate your account",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        username=user.username,
        expires_delta=access_token_expires,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {"message": "Authentication successful"}


@login_router.get("/protected")
async def protected_route(_: str = Depends(verify_user_token)):
    return {"Response": True}
