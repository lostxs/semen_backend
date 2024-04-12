import uuid

from pydantic import BaseModel, EmailStr

#########################
# BLOCK WITH API MODELS #
#########################


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True


class ShowUser(TunedModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    is_active: bool


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
