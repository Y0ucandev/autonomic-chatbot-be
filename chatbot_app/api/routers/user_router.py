from fastapi import APIRouter
from fastapi import Depends, HTTPException, Request, status
from datetime import datetime, timedelta, timezone
from typing import Dict
from chatbot_app.startup import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import jwt

user_router = APIRouter()


def create_access_token(data: Dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(request: Request) -> Dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = auth_header.split(" ")[1]
    return verify_token(token)


@user_router.post("/auth")
def get_token() -> Dict[str, str]:
    user_data = {"sub": "test@example.com"}
    token = create_access_token(user_data)
    return {"access_token": token, "token_type": "bearer"}


@user_router.get("/protected")
def protected_route(user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
    return {"message": "This is a protected route", "user": str(user)}
