from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions.auth import verify_user_token, get_user_details_by_username
from api.actions.user import _create_new_user, _activate_user_account
from api.schemas import ShowUser, UserCreate
from db.session import get_db

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
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="An error occurred while processing your request."
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        )


@user_router.post("/activate")
async def activate_account(
    user_id: UUID, code: str, db: AsyncSession = Depends(get_db)
) -> Union[dict, None]:
    try:
        await _activate_user_account(user_id, code, db)
        return {"message": "Account activated successfully"}
    except ValueError as e:
        if "Invalid activation code" in str(e):
            raise HTTPException(status_code=400, detail="Invalid activation code")
        elif "Activation code expired" in str(e):
            raise HTTPException(status_code=402, detail="Activation code expired")
    except NoResultFound:
        raise HTTPException(status_code=404, detail="User not found")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="An error occurred while processing your request."
        )


@user_router.get("/current_user")
async def get_current_user_route(
    username: str = Depends(verify_user_token), db: AsyncSession = Depends(get_db)
):
    user = await get_user_details_by_username(db, username)
    return {
        "user": {
            "email": user.email,
            "username": user.username,
            "user_id": user.user_id,
        }
    }
