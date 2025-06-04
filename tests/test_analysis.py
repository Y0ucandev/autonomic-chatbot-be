import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from chatbot_app.main import app
from chatbot_app.db.models import Base, User
from chatbot_app.api.routers.analysis_router import get_db
from chatbot_app.services.analysis_service import analyze_sentiment


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(test_db):
    db = SessionTesting()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(session):
    user = User(
        email="test@example.com",
        name="Test User",
        age=25,
        gender="female",
        hashed_password="hashed_password",
        role="user",
        sub="test@example.com",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_sentiment_post_and_get(client, test_user):
    with patch(
        "chatbot_app.api.routers.analysis_router.analyze_sentiment",
        new_callable=AsyncMock,
    ) as mock_analyze_sentiment:
        mock_analyze_sentiment.side_effect = [2, 6]

        payload = {
            "conversation_id": "conv-combined-123",
            "messages": [
                "I feel really bad today.",
                "Nothing's working.",
                "Just want to sleep.",
                "But I got a coffee.",
                "Started feeling better.",
                "Now I'm kind of okay.",
            ],
            "user_id": test_user.id,
        }

        response = client.post("/analysis/sentiment", json=payload)
        assert response.status_code == 200

        get_response = client.get("/analysis/sentiment/conv-combined-123")
        assert get_response.status_code == 200
        data = get_response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        first_record = data[0]
        assert first_record["conversation_id"] == "conv-combined-123"
        assert first_record["start_state"] == 2
        assert first_record["end_state"] == 6


def test_post_sentiment_too_few_messages(client, test_user):
    payload = {
        "conversation_id": "conv-too-short",
        "messages": ["Too short.", "Only two."],
        "user_id": test_user.id,
    }

    response = client.post("/analysis/sentiment", json=payload)
    assert response.status_code == 400
    assert "At least 3 messages are needed" in response.text


def test_get_sentiment_not_found(client):
    response = client.get("/analysis/sentiment/non-existent-conv")
    assert response.status_code == 404
    assert "Conversation not found" in response.text


@pytest.mark.asyncio
@patch(
    "chatbot_app.services.analysis_service.client_ai.chat.completions.create",
    new_callable=AsyncMock,
)
async def test_analyze_sentiment_success(mock_create):
    mock_response = AsyncMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="7"))]
    mock_create.return_value = mock_response

    messages = [
        "I had a pretty good day!",
        "Feeling optimistic about the future.",
        "Looking forward to the weekend.",
    ]

    result = await analyze_sentiment(messages)
    assert result == 7


@pytest.mark.asyncio
async def test_analyze_sentiment_too_few_messages():
    messages = ["Only one message"]
    with pytest.raises(ValueError, match="There must be at least 3 messages"):
        await analyze_sentiment(messages)
