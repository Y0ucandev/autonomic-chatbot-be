import time
import jwt

from chatbot_app.startup import SECRET_KEY, ALGORITHM
from fastapi.testclient import TestClient
from datetime import timedelta, timezone, datetime
from chatbot_app.main import app
from unittest.mock import patch
from chatbot_app.api.routers.user_router import create_access_token


client = TestClient(app)


def test_get_token():
    response = client.post("/users/auth")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_protected_route_without_token():
    response = client.get("/users/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization header"


def test_protected_route_with_valid_token():
    token_response = client.post("/users/auth")
    token = token_response.json()["access_token"]
    response = client.get(
        "/users/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "This is a protected route"


def test_protected_route_with_invalid_token():
    response = client.get(
        "/users/protected", headers={"Authorization": "Bearer invalid token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@patch("chatbot_app.api.routers.user_router.create_access_token")
def test_protected_route_with_expired_token(mock_create_token):

    mock_create_token.return_value = create_access_token(
        {"sub": "test@example.com", "role": "user"}, expires_delta=timedelta(seconds=1)
    )

    token_response = client.post("/users/auth")
    token = token_response.json()["access_token"]
    time.sleep(3)
    response = client.get(
        "/users/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_refresh_with_expired_token():
    expired_payload = {
        "sub": "test@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    response = client.post(
        "/users/refresh_token", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
