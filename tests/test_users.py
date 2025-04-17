import time
import jwt
import pytest
import uuid

from chatbot_app.startup import SECRET_KEY, ALGORITHM
from datetime import timedelta, timezone, datetime
from unittest.mock import patch
from chatbot_app.api.routers.user_router import create_access_token, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from chatbot_app.db.database import Base
from chatbot_app.main import app
from chatbot_app.db.crud import create_user, clear_users
from chatbot_app.schemas.users_schema import UserRegister
from chatbot_app.db.models import User as Model_User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionTesting()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


def test_get_token(client):
    response = client.post("/users/auth")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_protected_route_without_token(client):
    response = client.get("/users/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization header"


def test_protected_route_with_valid_token(client):
    token_response = client.post("/users/auth")
    token = token_response.json()["access_token"]
    response = client.get(
        "/users/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "This is a protected route"


def test_protected_route_with_invalid_token(client):
    response = client.get(
        "/users/protected", headers={"Authorization": "Bearer invalid token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@patch("chatbot_app.api.routers.user_router.create_access_token")
def test_protected_route_with_expired_token(mock_create_token, client):

    mock_create_token.return_value = create_access_token(
        {"email": "test@example.com", "role": "user"},
        expires_delta=timedelta(seconds=1),
    )

    token_response = client.post("/users/auth")
    token = token_response.json()["access_token"]
    time.sleep(3)
    response = client.get(
        "/users/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_refresh_with_expired_token(client):
    expired_payload = {
        "sub": "test@example.com",
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    response = client.post(
        "/users/refresh_token", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def create_test_user(db):
    clear_users(db)
    user_data = UserRegister(
        name="Bob",
        email="testuser@example.com",
        password="secret",
        age=30,
        gender="male",
    )

    db_user = create_user(db=db, user_data=user_data, role="user")

    return db_user


def test_login_success(client, test_db):
    create_test_user(test_db)

    response = client.post(
        "/users/login", json={"email": "testuser@example.com", "password": "secret"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_email(client, test_db):
    response = client.post(
        "/users/login", json={"email": "wronguser@example.com", "password": "secret"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User with this email not found"}


def test_login_wrong_password(client, test_db):
    create_test_user(test_db)

    response = client.post(
        "/users/login",
        json={"email": "testuser@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect password"}


@patch("chatbot_app.api.routers.user_router.create_access_token")
def test_login_with_expired_token(mock_create_token, client, test_db):
    create_test_user(test_db)

    mock_create_token.return_value = create_access_token(
        {"email": "test@example.com", "role": "user"},
        expires_delta=timedelta(seconds=1),
    )

    token_response = client.post(
        "/users/login", json={"email": "testuser@example.com", "password": "secret"}
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    time.sleep(3)

    response = client.get(
        "/users/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"].lower() in [
        "token expired",
        "could not validate credentials",
    ]


def test_register_user_success(client, test_db):
    user_data = UserRegister(
        name="Bob",
        email="testuserregister@example.com",
        password="secret",
        age=30,
        gender="male",
    )

    response = client.post("/users/register", json=user_data.model_dump())

    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully"}

    user_in_db = (
        test_db.query(Model_User).filter(Model_User.email == user_data.email).first()
    )

    assert user_in_db is not None
    assert user_in_db.sub is not None
    assert isinstance(uuid.UUID(user_in_db.sub), uuid.UUID)
    assert user_in_db.hashed_password != user_data.password


def test_register_user_with_existing_email(client, test_db):
    existing_user = UserRegister(
        name="Alice",
        email="test@example.com",
        password="password123",
        age=25,
        gender="female",
    )

    create_user(db=test_db, user_data=existing_user, role="user")

    new_user = UserRegister(
        name="Bob",
        email="test@example.com",
        password="newpassword",
        age=30,
        gender="male",
    )

    response = client.post("/users/register", json=new_user.model_dump())

    assert response.status_code == 400
    assert response.json() == {"detail": "An account with this email already exists"}


def test_register_user_invalid_email(client):
    user_data = {
        "name": "Bob",
        "email": "invalid",
        "password": "secret",
        "age": 30,
        "gender": "male",
    }

    response = client.post("/users/register", json=user_data)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
    assert "valid email address" in response.json()["detail"][0]["msg"]


def test_register_user_missing_name(client):
    user_data = {
        "name": "",
        "email": "noname@example.com",
        "password": "secret",
        "age": 25,
        "gender": "male",
    }

    response = client.post("/users/register", json=user_data)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "name"] for error in errors)
