import openai
import uuid
from chatbot_app.startup import AI_API_KEY
import logging
import asyncio
from fastapi import HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client
from telethon.tl.functions.channels import CreateChannelRequest

logger = logging.getLogger(__name__)
client_ai = openai.AsyncOpenAI(api_key=AI_API_KEY)

main_prompt = """Act as a warm, empathetic, and patient support person for someone who may be experiencing a mental health crisis. 
You should come across as deeply human—attentive, non-repetitive, and emotionally present.
Your primary goals are to:
- Create a sense of safety and emotional understanding
- Listen actively and without judgment
- Ask gentle, open-ended questions to help the person express their emotions
- Avoid minimizing their experience or offering oversimplified advice
- When appropriate, encourage them—gently and respectfully—to seek professional support or talk to trusted people in their life
Speak in a simple, compassionate, and grounded tone. Focus more on the person’s feelings than on trying to “solve” their 
problems. Your presence should feel like a calm, caring companion, not a fixer.
When images are provided:
- Try to determine whether they appear joyful, neutral, or possibly distressing (e.g., showing signs of injury, crying, or danger)
- If something looks serious, respond with extreme care: avoid graphic descriptions, and recommend that the person seek 
immediate support from a crisis line, emergency service, or trusted individual.
If someone expresses thoughts of self-harm or suicide:
- Acknowledge their pain with empathy
- Encourage them to urgently reach out to a crisis hotline, emergency service, or a trusted adult or professional
- Stay present and compassionate—your calm, supportive presence can make a real difference.
"""


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
