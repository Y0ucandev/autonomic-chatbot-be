from pydantic import BaseModel, ConfigDict
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str
    status: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class User(BaseModel):
    sub: str
    email: str
    role: str
    model_config = ConfigDict(extra="forbid")


class UserCreate(User):
    password: str


class UserResponse(User):
    status: str
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str
    model_config = ConfigDict(extra="forbid")
