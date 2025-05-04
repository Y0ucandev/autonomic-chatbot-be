import logging
import asyncio
from fastapi import APIRouter, Query, HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client

message_router = APIRouter()

logger = logging.getLogger(__name__)


async def connect_client(retries=3, delay=1):
    for _ in range(retries):
        if client.is_connected():
            return
        await client.connect()
        await asyncio.sleep(delay)
    if not client.is_connected():
        raise HTTPException(status_code=500, detail="Failed to connect to Telegram")


@message_router.get("/history", response_model=MessageHistoryResponse)
async def get_message_history(
    user_id: int = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset_id: int = Query(default=0),
):
    await connect_client()

    messages = []

    try:
        entity = await client.get_entity(user_id)

        async for msg in client.iter_messages(
            entity=entity, limit=limit, offset_id=offset_id
        ):
            if msg.message:
                message = TelegramMessage(
                    id=msg.id,
                    sender_id=msg.sender_id or 0,
                    chat_id=msg.chat_id or 0,
                    text=msg.message,
                    date=msg.date,
                )
                messages.append(message.model_dump())
        next_offset_id = messages[-1]["id"] if messages else offset_id

    except Exception:
        logger.error("Error while fetching messages", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving messages from Telegram",
        )

    return MessageHistoryResponse(messages=messages, next_offset_id=next_offset_id)
