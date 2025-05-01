import logging
from fastapi import APIRouter, Query, HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client

message_router = APIRouter()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def connect_client():
    if not client.is_connected():
        await client.connect()
        if not client.is_connected():
            raise HTTPException(status_code=500, detail="Failed to connect to Telegram")


@message_router.get("/history", response_model=MessageHistoryResponse)
async def get_message_history(
    chat: str = Query(default="me"),
    limit: int = Query(default=20, ge=1, le=100),
    offset_id: int = Query(default=0),
):
    await connect_client()

    messages = []
    next_offset_id = None

    try:
        async for msg in client.iter_messages(
            entity=chat, limit=limit, offset_id=offset_id
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
        if messages:
            next_offset_id = messages[-1]["id"]

    except Exception as e:
        logger.error(f"Error while fetching messages: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving messages from Telegram",
        )

    return MessageHistoryResponse(messages=messages, next_offset_id=next_offset_id)
