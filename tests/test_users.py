import time
import jwt
import pytest

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
from chatbot_app.schemas.users_schema import UserCreate


@pytest.fixture(scope="module")
def test_db():
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    yield db

    db.close()

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    return client


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
        {"email": "test@example.com", "role": "user"}, expires_delta=timedelta(seconds=1)
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
    user_in = UserCreate(sub="testuser@example.com", email="testuser@example.com", password="secret", role="user")

    db_user = create_user(db, sub=user_in.sub, email=user_in.email, password=user_in.password, role=user_in.role)

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

    assert response.status_code == 401
    assert response.json() == {"detail": "Email not found"}


def test_login_wrong_password(client, test_db):
    create_test_user(test_db)

    response = client.post(
        "/users/login",
        json={"email": "testuser@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect password"}
