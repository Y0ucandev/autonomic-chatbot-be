from fastapi.testclient import TestClient
from chatbot_app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome"}


def test_read_item():
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "q": None}

    response_with_query = client.get("/items/1?q=test")
    assert response_with_query.status_code == 200
    assert response_with_query.json() == {"item_id": 1, "q": "test"}


def test_404_not_found():
    response = client.get("/nonexistent_endpoint")
    assert response.status_code == 404


def test_query_params():
    response = client.get("/items/1?q=")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "q": ""}

    response_with_q1 = client.get("/items/1?q=test1")
    assert response_with_q1.status_code == 200
    assert response_with_q1.json() == {"item_id": 1, "q": "test1"}

    response_with_q2 = client.get("/items/1?q=test2")
    assert response_with_q2.status_code == 200
    assert response_with_q2.json() == {"item_id": 1, "q": "test2"}


def test_init_db():
    response = client.get("/items/")
    assert response.json() == {"message": "Async DB session initialized"}
