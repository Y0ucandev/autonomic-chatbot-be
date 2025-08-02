import jwt
import random

from chatbot_app.startup import SECRET_KEY, ALGORITHM
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import Response
from typing import Dict
from chatbot_app.services.user_service import (
    create_access_token,
    get_current_user,
    authenticate_user,
    get_user_by_email,
)
from chatbot_app.schemas.users_schema import (
    Token,
    User,
    LoginRequest,
    UserRegister,
    UserRole,
)
from sqlalchemy.orm import Session
from chatbot_app.db.database import SessionLocal
from chatbot_app.db.crud import create_user
from chatbot_app.db.models import User as Model_User

user_router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@user_router.post("/auth")
def get_token() -> Token:
    user_data = {"sub": "test@example.com", "email": "test@example.com", "role": "user"}
    token = create_access_token(user_data)
    return {"access_token": token, "token_type": "bearer", "user_id": 123}


@user_router.get("/protected")
def protected_route(user: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"message": "This is a protected route", "user": user.sub}


@user_router.post("/refresh_token")
def refresh_token(request: Request, db: Session = Depends(get_db)) -> Token:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    refresh_token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user_email = payload.get("email") or payload.get("sub")
    if not user_email:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    user = get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = {"sub": payload["sub"], "role": payload["role"]}
    new_access_token = create_access_token(user_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user_id": user.id,
    }


@user_router.post("/login")
def login(login_request: LoginRequest, db: Session = Depends(get_db)) -> Token:
    auth_result = authenticate_user(db, login_request.email, login_request.password)

    access_token = create_access_token(
        data={
            "sub": auth_result.email,
            "email": auth_result.email,
            "role": auth_result.role,
            "name": auth_result.name,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "status": "success",
        "user_id": auth_result.id,
    }


@user_router.post("/register")
def register(user_create: UserRegister, db: Session = Depends(get_db)) -> Response:
    if db.query(Model_User).filter(Model_User.email == user_create.email).first():
        raise HTTPException(
            status_code=400, detail="An account with this email already exists"
        )

    create_user(db=db, user_data=user_create, role=UserRole.user)

    return Response(status_code=200)


@user_router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"name": current_user.name, "email": current_user.email}


@user_router.post("/temporary_user_id")
def generate_temporary_user_id(db: Session = Depends(get_db)) -> Dict[str, int]:
    while True:
        temp_id = random.randint(-2_000_000_000, -1)
        exists = db.query(Model_User).filter(Model_User.id == temp_id).first()
        if not exists:
            break
    return {"temporary_user_id": temp_id}
