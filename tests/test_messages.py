import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from chatbot_app.main import app


@pytest.mark.asyncio
async def test_get_history_success():
    mock_message = MagicMock()
    mock_message.id = 111
    mock_message.message = "Hello"
    mock_message.sender_id = 123456
    mock_message.chat_id = 654321
    mock_message.date = datetime.now(timezone.utc)
    mock_message.photo = None

    async def fake_iter_messages(*args, **kwargs):
        yield mock_message

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

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert data["messages"][0]["text"] == "Hello"
        assert data["messages"][0]["sender_id"] == 123456
        assert "next_offset_id" in data
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
