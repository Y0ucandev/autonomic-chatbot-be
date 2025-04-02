from fastapi.testclient import TestClient
from chatbot_app.main import app

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
    response = client.get("/users/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "This is a protected route"


def test_protected_route_with_invalid_token():
    response = client.get("/users/protected", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"
