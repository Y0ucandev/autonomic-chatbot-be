import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from chatbot_app.main import app
from chatbot_app.services.message_service import create_private_channel
from chatbot_app.telegram_listener import handle_new_message
from collections.abc import AsyncIterator
from types import SimpleNamespace


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


@pytest.mark.asyncio
async def test_create_private_channel_success():
    mock_channel = AsyncMock()
    mock_channel.id = 12345

    mock_result = AsyncMock()
    mock_result.chats = [mock_channel]

    with patch(
        "chatbot_app.services.message_service.client", new_callable=AsyncMock
    ) as mock_client, patch(
        "chatbot_app.services.message_service.CreateChannelRequest"
    ) as mock_request:

        mock_client.return_value = mock_result

        result = await create_private_channel("TestChannel", "Desc")

        assert result.id == 12345
        mock_request.assert_called_once_with(
            title="TestChannel", about="Desc", megagroup=False
        )


@pytest.mark.asyncio
async def test_handle_new_message_creates_anon_channel_and_replies():
    mock_event = AsyncMock()
    mock_msg = AsyncMock()
    mock_msg.id = 1
    mock_msg.sender_id = None
    mock_msg.chat_id = 0
    mock_msg.message = "Hello from anon"
    mock_msg.date = "2025-05-29"
    mock_event.message = mock_msg
    mock_event.sender_id = None
    mock_client = AsyncMock()

    mock_client.iter_messages = lambda *args, **kwargs: FakeAsyncIterator(
        [
            SimpleNamespace(
                id=1,
                message="hi",
                sender_id=123,
                chat_id=456,
                date="2025-05-29",
                photo=None,
            )
        ]
    )

    mock_client.is_connected = lambda: True
    mock_client.connect = AsyncMock()

    with patch(
        "chatbot_app.telegram_listener.create_private_channel", new_callable=AsyncMock
    ) as mock_create_channel, patch(
        "chatbot_app.telegram_listener.generate_anon_id", return_value="anon-uuid"
    ), patch(
        "chatbot_app.telegram_listener.generate_ai_response", return_value="AI reply"
    ), patch(
        "chatbot_app.services.message_service.client", mock_client
    ), patch(
        "chatbot_app.telegram_listener.client.get_me", new_callable=AsyncMock
    ) as mock_get_me, patch(
        "chatbot_app.telegram_listener.client.send_message", new_callable=AsyncMock
    ) as mock_send_message:

        mock_channel = AsyncMock()
        mock_channel.id = 77777
        mock_create_channel.return_value = mock_channel
        mock_get_me.return_value.id = 123456

        await handle_new_message(mock_event)

        mock_create_channel.assert_called_once_with(
            "AnonUser-anon-uuid", "Channel for anonymous user"
        )
        assert mock_send_message.call_count == 2
        mock_send_message.assert_any_call(
            mock_channel.id, "Anonymous user: Hello from anon"
        )
        mock_send_message.assert_any_call(mock_channel.id, "AI reply")
