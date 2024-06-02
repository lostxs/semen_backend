from typing import Union
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from api.schemas import ShowUser
from api.schemas import UserCreate
from api.schemas import ActivationCodeData
from .dependencies import get_current_user
from .actions import _create_new_user
from .actions import _activate_user_account

user_router = APIRouter()


@user_router.post("/", response_model=ShowUser)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> ShowUser:
    try:
        return await _create_new_user(body, db)
    except IntegrityError as err:
        await db.rollback()
        err_detail = str(err.orig)
        if "users_username_key" in err_detail:
            detail = "A user with this username already exists."
            raise HTTPException(status_code=400, detail=detail)
        elif "users_email_key" in err_detail:
            detail = "A user with this email already exists."
            raise HTTPException(status_code=400, detail=detail)
        else:
            detail = "An internal server error occurred."
            raise HTTPException(
                status_code=400 if "already exists" in detail else 500, detail=detail
            )


@user_router.post("/activate")
async def activate_account(
    data: ActivationCodeData, db: AsyncSession = Depends(get_db)
) -> Union[dict, None]:
    user_id = data.user_id
    code = data.code
    try:
        await _activate_user_account(user_id, code, db)
        return {"message": "Account activated successfully"}
    except ValueError as e:
        await db.rollback()
        if "Invalid or already used activation code." in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        elif "Activation code expired" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
    except NoResultFound:
        raise HTTPException(status_code=404, detail="No results found.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="An error occurred while processing your request."
        )


@user_router.get("/current_user", response_model=ShowUser)
async def get_user(current_user: ShowUser = Depends(get_current_user)):
    return current_user
