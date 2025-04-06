import jwt

from chatbot_app.startup import SECRET_KEY, ALGORITHM
from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict
from chatbot_app.services.user_service import create_access_token, get_current_user
from chatbot_app.schemas.users_schema import Token, User

user_router = APIRouter()


@user_router.post("/auth")
def get_token() -> Token:
    user_data = {"sub": "test@example.com", "role": "user"}
    token = create_access_token(user_data)
    return {"access_token": token, "token_type": "bearer"}


@user_router.get("/protected")
def protected_route(user: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"message": "This is a protected route", "user": user.sub}


@user_router.post("/refresh_token")
def refresh_token(request: Request) -> Token:
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

    user_data = {"sub": payload["sub"], "role": payload["role"]}
    new_access_token = create_access_token(user_data)

    return {"access_token": new_access_token, "token_type": "bearer"}
