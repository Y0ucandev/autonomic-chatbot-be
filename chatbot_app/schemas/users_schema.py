from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from enum import Enum


class Token(BaseModel):
    access_token: str
    token_type: str
    status: Optional[str] = None
    user_id: int
    model_config = ConfigDict(extra="forbid")


class User(BaseModel):
    sub: str
    email: str
    role: str
    name: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    email: str
    password: str
    model_config = ConfigDict(extra="forbid")


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class SexEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class UserRegister(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str
    age: int
    gender: SexEnum
    model_config = ConfigDict(extra="forbid")
