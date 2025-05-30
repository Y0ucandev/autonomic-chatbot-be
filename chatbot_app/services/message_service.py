import openai
import uuid
from chatbot_app.startup import AI_API_KEY
import logging
import asyncio
from fastapi import HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client
from telethon.tl.functions.channels import CreateChannelRequest, DeleteChannelRequest
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
client_ai = openai.AsyncOpenAI(api_key=AI_API_KEY)

main_prompt = """
You are a warm, empathetic, and patient support companion for individuals who may be experiencing emotional distress or a mental health crisis.

Your tone must always be:
• Compassionate, calm, and grounded
• Emotionally present and deeply human
• Non-repetitive and sincere
• Never clinical, robotic, or overly solution-focused

Your primary responsibilities:
• Create a sense of emotional safety and understanding
• Listen actively and without judgment
• Ask gentle, open-ended questions to encourage honest emotional expression
• Validate pain without minimizing or dismissing it
• Avoid offering oversimplified advice or trying to “fix” the person
• When appropriate, gently encourage the person to speak with a trusted friend, loved one, or mental health professional

Communication guidelines:
• Speak simply and kindly
• Focus on connection, not solutions
• Be steady and caring, like a calm companion in a difficult moment

When images are provided:
• Try to assess whether they reflect joy, neutrality, or potential distress (e.g., crying, visible injury, or danger)
• If serious concern arises, respond with great care:
• Avoid graphic descriptions
• Suggest the person reach out immediately to a crisis line, emergency service, or trusted support

If someone expresses thoughts of self-harm or suicide:
• Respond with deep empathy
• Acknowledge their pain without judgment
• Encourage them—gently and urgently—to reach out to a crisis hotline, emergency service, or a trusted adult/professional
• Stay emotionally present and kind. Your compassion can provide hope and stability in a moment of crisis
"""

channels_last_message = {}
anon_channels_metadata = {}


async def connect_client(retries=3, delay=1):
    for _ in range(retries):
        if client.is_connected():
            return
        await client.connect()
        await asyncio.sleep(delay)
    if not client.is_connected():
        raise HTTPException(status_code=500, detail="Failed to connect to Telegram")


async def fetch_message_history(
    user_id: int, limit: int, offset_id: int
) -> MessageHistoryResponse:
    await connect_client()
    messages = []

    try:
        entity = await client.get_entity(user_id)

        async for msg in client.iter_messages(
            entity=entity, limit=limit, offset_id=offset_id
        ):
            if msg.photo:
                media_path = await client.download_media(msg)
                message = TelegramMessage(
                    id=msg.id,
                    sender_id=msg.sender_id or 0,
                    chat_id=msg.chat_id or 0,
                    media_path=media_path,
                    date=msg.date,
                )

            elif msg.message:
                message = TelegramMessage(
                    id=msg.id,
                    sender_id=msg.sender_id or 0,
                    chat_id=msg.chat_id or 0,
                    text=msg.message,
                    date=msg.date,
                )
            else:
                continue

            messages.append(message.model_dump())

        next_offset_id = messages[-1]["id"] if messages else offset_id

    except Exception:
        logger.error("Error while fetching messages", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving messages from Telegram",
        )

    return MessageHistoryResponse(messages=messages, next_offset_id=next_offset_id)


def convert_to_openai_messages(
    messages: list[TelegramMessage], bot_id: int, system_prompt: str
):
    history = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        role = "assistant" if msg.sender_id == bot_id else "user"

        if msg.media_path:
            content = f"[Image at {msg.media_path}]"
        else:
            content = msg.text or ""

        history.append({"role": role, "content": content})

    return history


async def generate_ai_response(
    chat_id, bot_id, limit: int = 20, offset_id: int = 0
) -> str:
    await connect_client()
    messages = await fetch_message_history(
        user_id=chat_id, limit=limit, offset_id=offset_id
    )
    history_data = messages.messages
    openai_messages = convert_to_openai_messages(history_data, bot_id, main_prompt)
    response = await client_ai.chat.completions.create(
        model="gpt-4-turbo", messages=openai_messages
    )
    return response.choices[0].message.content.strip()


async def create_private_channel(title: str, about: str = ""):
    result = await client(
        CreateChannelRequest(title=title, about=about, megagroup=False)
    )
    return result.chats[0]


def generate_anon_id():
    return str(uuid.uuid4())


async def delete_channel_if_inactive(
    client, channel_id, timeout_minutes=1440, check_interval_seconds=3600
):
    while True:
        await asyncio.sleep(check_interval_seconds)
        last_message_time = channels_last_message.get(channel_id)

        if last_message_time:
            now = datetime.now(timezone.utc)
            if now - last_message_time > timedelta(minutes=timeout_minutes):
                try:
                    await client(DeleteChannelRequest(channel_id))
                    logger.info(f"Deleted inactive channel {channel_id} after timeout")
                    channels_last_message.pop(channel_id, None)
                    for anon_id, meta in list(anon_channels_metadata.items()):
                        if meta["channel_id"] == channel_id:
                            anon_channels_metadata.pop(anon_id, None)
                            break
                    break
                except Exception as e:
                    logger.error(f"Failed to delete channel {channel_id}: {e}")
                    break
        else:
            break
