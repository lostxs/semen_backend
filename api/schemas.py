import uuid
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import constr


#########################
# BLOCK WITH API MODELS #
#########################


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True


class ShowUser(TunedModel):
    # user_id: uuid.UUID
    username: str
    email: EmailStr
    is_active: bool

class ShowActivationCode(TunedModel):
    email: EmailStr
    username: str
    is_active: bool = False
    # code: str

class UserCreate(BaseModel):
    username: constr(min_length=1, max_length=50) # type: ignore
    email: EmailStr
    password: constr(min_length=6) # type: ignore


class ActivationCodeData(BaseModel):
    code: str
