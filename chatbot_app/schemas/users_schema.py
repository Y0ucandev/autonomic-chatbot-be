from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    sub: str
    email: str
    role: str


class UserCreate(User):
    email: str
    password: str
    role: str


class UserResponse(User):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str
