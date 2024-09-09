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
from .actions import _create_new_activation_code, _create_new_user
from .actions import _activate_user_account

user_router = APIRouter()


@user_router.post("/", response_model=ShowUser)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> ShowUser:
    result = await _create_new_activation_code(body, db)
    
    if result == "email_exists":
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует.")
    elif result == "username_exists":
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует.")
    
    return result


@user_router.post("/activate")
async def activate_account(data: ActivationCodeData, db: AsyncSession = Depends(get_db)) -> dict:
    code = data.code
    try:
        await _activate_user_account(code, db)
        return {"message": "Аккаунт успешно активирован."}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Код активации не найден.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Произошла ошибка при активации аккаунта. Попробуйте еще раз."
        )


@user_router.get("/current_user", response_model=ShowUser)
async def get_user(current_user: ShowUser = Depends(get_current_user)):
    return current_user
