import pytest
from fastapi import status, HTTPException
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from chatbot_app.main import app
from collections.abc import AsyncIterator
from chatbot_app.services.message_service import (
    extract_direction_and_user_id,
    convert_to_openai_messages,
    generate_ai_response,
    add_user_facts,
)
from chatbot_app.schemas.message_schema import TelegramMessage
from chatbot_app.api.routers.message_router import client, OPERATOR_CHAT_ID
from chatbot_app.db.models import FactRecord
import pytest_asyncio
from chatbot_app.db.models import Base
from chatbot_app.api.routers.message_router import get_db

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTesting = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


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


@pytest_asyncio.fixture
async def test_client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("[from 12345] Hello!", ("from", "12345")),
        ("[to 98765] How are you?", ("to", "98765")),
        ("   [from 111]Hi", ("from", "111")),
        ("[to 00000]   Message", ("to", "00000")),
        ("No brackets here", None),
        ("[from ]", None),
        ("[from abc] message", None),
        ("[12345 from] test", None),
    ],
)
def test_extract_direction_and_user_id(text, expected):
    assert extract_direction_and_user_id(text) == expected


class FakeAsyncIterator(AsyncIterator):
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_get_history_success():
    mock_message = TelegramMessage(
        id=111,
        sender_id=123456,
        chat_id=654321,
        text="[to 123456] Hello",
        media_path=None,
        date=datetime.now(timezone.utc),
        user_id=None,
    )

    mock_full_history = MagicMock()
    mock_full_history.messages = [mock_message]
    mock_full_history.next_offset_id = 111

    with patch(
        "chatbot_app.api.routers.message_router.fetch_message_history",
        new=AsyncMock(return_value=mock_full_history),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/message/history?user_id=123456&limit=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert data["messages"][0]["text"] == "Hello"
        assert data["messages"][0]["sender_id"] == 123456
        assert data["next_offset_id"] == 111


@pytest.mark.asyncio
async def test_get_history_connection_fail():
    with patch(
        "chatbot_app.services.message_service.client.is_connected",
        side_effect=[False, False, False, False],
    ), patch(
        "chatbot_app.services.message_service.client.connect", new_callable=AsyncMock
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/message/history?user_id=123456&limit=1")

        assert response.status_code == 500
        assert "Failed to connect to Telegram" in response.text


@pytest.mark.asyncio
async def test_get_history_exception_during_fetch():
    async def fake_iter_messages(*args, **kwargs):
        raise Exception("Some Telegram error")
        yield

    with patch(
        "chatbot_app.services.message_service.client.iter_messages",
        new=fake_iter_messages,
    ), patch(
        "chatbot_app.services.message_service.client.is_connected", return_value=True
    ), patch(
        "chatbot_app.services.message_service.client.connect", new_callable=AsyncMock
    ), patch(
        "chatbot_app.services.message_service.client.get_entity",
        new_callable=AsyncMock,
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/message/history?user_id=123456&limit=1")

        assert response.status_code == 500
        assert "An error occurred while retrieving messages" in response.text


def test_convert_to_openai_messages():
    system_prompt = "You are a helpful assistant."

    messages = [
        TelegramMessage(
            id=1,
            sender_id=123,
            chat_id=456,
            text="[from 123] Hello",
            media_path=None,
            date=datetime.now(timezone.utc),
        ),
        TelegramMessage(
            id=2,
            sender_id=123,
            chat_id=456,
            text="[to 123] Hi there!",
            media_path=None,
            date=datetime.now(timezone.utc),
        ),
        TelegramMessage(
            id=3,
            sender_id=123,
            chat_id=456,
            text="Invalid message format",
            media_path=None,
            date=datetime.now(timezone.utc),
        ),
        TelegramMessage(
            id=4,
            sender_id=123,
            chat_id=456,
            text=None,
            media_path=None,
            date=datetime.now(timezone.utc),
        ),
    ]

    expected = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    result = convert_to_openai_messages(messages, system_prompt)
    assert result == expected


@pytest.mark.asyncio
async def test_generate_ai_response_success():
    mock_message = TelegramMessage(
        id=1,
        sender_id=123,
        chat_id=456,
        text="[from 789] Hello",
        media_path=None,
        date=datetime.now(timezone.utc),
        user_id=None,
    )

    mock_history = MagicMock()
    mock_history.messages = [mock_message]
    mock_history.next_offset_id = 1

    mock_ai_response = MagicMock()
    mock_ai_response.choices = [MagicMock(message=MagicMock(content="Hi there!"))]

    with patch(
        "chatbot_app.services.message_service.connect_client", new=AsyncMock()
    ), patch(
        "chatbot_app.services.message_service.fetch_message_history",
        new=AsyncMock(return_value=mock_history),
    ), patch(
        "chatbot_app.services.message_service.client_ai.chat.completions.create",
        new=AsyncMock(return_value=mock_ai_response),
    ), patch(
        "chatbot_app.services.message_service.main_prompt", "You are helpful."
    ):
        result = await generate_ai_response(app_user_id=789)

        assert result == "[to 789] Hi there!"


@pytest.mark.asyncio
async def test_generate_ai_response_failure():
    mock_message = TelegramMessage(
        id=1,
        sender_id=123,
        chat_id=456,
        text="[from 789] Hello",
        media_path=None,
        date=datetime.now(timezone.utc),
        user_id=None,
    )

    mock_history = MagicMock()
    mock_history.messages = [mock_message]

    with patch(
        "chatbot_app.services.message_service.connect_client", new=AsyncMock()
    ), patch(
        "chatbot_app.services.message_service.fetch_message_history",
        new=AsyncMock(return_value=mock_history),
    ), patch(
        "chatbot_app.services.message_service.client_ai.chat.completions.create",
        new=AsyncMock(side_effect=Exception("Connection error")),
    ), patch(
        "chatbot_app.services.message_service.main_prompt", "You are helpful."
    ):

        with pytest.raises(HTTPException) as exc_info:
            await generate_ai_response(app_user_id=789)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "AI response generation failed"


@pytest.mark.asyncio
async def test_send_message_success():
    payload = {"user_id": "123", "message": "Hello"}

    with patch.object(client, "is_connected", return_value=True), patch.object(
        client, "send_message", new=AsyncMock()
    ) as mock_send_message, patch(
        "chatbot_app.api.routers.message_router.generate_ai_response",
        new=AsyncMock(return_value="[to 123] AI response"),
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/message/send-message", json=payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
        mock_send_message.assert_any_call(int(OPERATOR_CHAT_ID), "[from 123] Hello")
        mock_send_message.assert_any_call(int(OPERATOR_CHAT_ID), "[to 123] AI response")


@pytest.mark.asyncio
async def test_send_message_value_error():
    payload = {"user_id": "123", "message": "Hello"}

    with patch.object(client, "is_connected", return_value=True), patch.object(
        client, "send_message", new=AsyncMock()
    ), patch(
        "chatbot_app.api.routers.message_router.generate_ai_response",
        new=AsyncMock(side_effect=ValueError("Invalid user_id")),
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/message/send-message", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid user_id"


@pytest.mark.asyncio
async def test_send_message_connection_error():
    payload = {"user_id": "123", "message": "Hello"}

    with patch.object(client, "is_connected", return_value=True), patch.object(
        client, "send_message", new=AsyncMock()
    ), patch(
        "chatbot_app.api.routers.message_router.generate_ai_response",
        new=AsyncMock(side_effect=ConnectionError("Connection lost")),
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/message/send-message", json=payload)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["detail"] == "Client connection failed"


@pytest.mark.asyncio
async def test_send_message_unexpected_error():
    payload = {"user_id": "123", "message": "Hello"}

    with patch.object(client, "is_connected", return_value=True), patch.object(
        client, "send_message", new=AsyncMock()
    ), patch(
        "chatbot_app.api.routers.message_router.generate_ai_response",
        new=AsyncMock(side_effect=Exception("Boom")),
    ):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/message/send-message", json=payload)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Internal server error"


@patch(
    "chatbot_app.services.message_service.client_ai.chat.completions.create",
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_add_user_facts_success(mock_create, session):
    mock_create.return_value.choices = [
        MagicMock(
            message=MagicMock(content="I live in Berlin.\nI work as a developer.")
        )
    ]

    await add_user_facts(user_id=1, user_message="I live in Berlin", db=session)

    facts = session.query(FactRecord).all()
    assert len(facts) == 2


@pytest.mark.asyncio
async def test_get_user_facts(test_client: AsyncClient, session):
    user_id = 123
    facts_texts = ["Fact one", "Fact two"]
    for fact_text in facts_texts:
        session.add(FactRecord(user_id=user_id, user_fact=fact_text))
    session.commit()
    response = await test_client.get(f"/message/user-facts/{user_id}")

    assert response.status_code == 200
    json_data = response.json()
    assert isinstance(json_data, list)
    assert set(json_data) == set(facts_texts)


@pytest.mark.asyncio
async def test_get_user_facts_db_error(monkeypatch, test_client):
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("DB error")

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    user_id = 123
    response = await test_client.get(f"message/user-facts/{user_id}")

    assert response.status_code == 500
    assert response.json() == {"detail": "Database query failed"}

    app.dependency_overrides.clear()
