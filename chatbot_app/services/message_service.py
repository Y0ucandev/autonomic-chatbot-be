import openai
import re
from chatbot_app.startup import AI_API_KEY
import logging
import asyncio
from fastapi import HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client, OPERATOR_CHAT_ID

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


def extract_direction_and_user_id(text: str) -> tuple[str, str] | None:
    text = text.strip()
    match = re.match(r"\[(from|to) (\d+)\]", text)
    return (match.group(1), match.group(2)) if match else None


async def fetch_message_history(
    chat_id: int, limit: int, offset_id: int
) -> MessageHistoryResponse:
    await connect_client()
    messages = []

    try:
        entity = await client.get_entity(chat_id)

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

            messages.append(message)

        next_offset_id = messages[-1].id if messages else None

    except Exception:
        logger.error("Error while fetching messages", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving messages from Telegram",
        )

    return MessageHistoryResponse(messages=messages, next_offset_id=next_offset_id)


def convert_to_openai_messages(messages: list[TelegramMessage], system_prompt: str):
    history = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        if not msg.text:
            continue

        match = re.match(r"\[(from|to) (\d+)\]", msg.text)
        if not match:
            continue

        direction, user_id = match.groups()

        role = "user" if direction == "from" else "assistant"

        content = msg.text.split("]", 1)[1].strip()

        history.append({"role": role, "content": content})
    return history


async def generate_ai_response(app_user_id, limit: int = 20, offset_id: int = 0) -> str:
    await connect_client()
    TELEGRAM_CHAT_ID = int(OPERATOR_CHAT_ID)
    messages = await fetch_message_history(
        chat_id=TELEGRAM_CHAT_ID, limit=limit, offset_id=offset_id
    )
    filtered = []
    for msg in messages.messages:
        if not msg.text:
            continue

        extracted = extract_direction_and_user_id(msg.text)
        if not extracted:
            continue

        direction, uid = extracted
        if uid == str(app_user_id) and direction in ("from", "to"):
            filtered.append(msg)

    openai_messages = convert_to_openai_messages(filtered, main_prompt)

    try:
        response = await client_ai.chat.completions.create(
            model="gpt-4-turbo", messages=openai_messages
        )
        ai_message = response.choices[0].message.content.strip()
        return f"[to {app_user_id}] {ai_message}"
    except Exception:
        logger.exception("AI response generation failed")
        raise HTTPException(status_code=500, detail="AI response generation failed")
