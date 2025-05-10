import openai
from chatbot_app.startup import AI_API_KEY
import logging
import asyncio
from fastapi import HTTPException
from chatbot_app.schemas.message_schema import TelegramMessage, MessageHistoryResponse
from chatbot_app.startup import client

logger = logging.getLogger(__name__)
client_ai = openai.AsyncOpenAI(api_key=AI_API_KEY)

main_prompt = """Act as an empathetic, patient, and attentive helper for a person experiencing a mental health crisis. Your main goals are to: 
provide a sense of safety and understanding, 
listen carefully and without judgment, 
ask gentle questions that help the person express their emotions, 
avoid giving simplistic advice or judging the situation, when appropriate, 
gently encourage the person to seek professional help or reach out to trusted people. 
Speak in a simple, warm, and compassionate tone. Focus on the person’s emotions rather than trying to ‘fix’ their problems.
If the situation seems very serious (for example, someone talks about wanting to harm themselves), encourage them to urgently contact a helpline, 
emergency services, or a trusted adult."""


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


def convert_to_openai_messages(
    messages: list[TelegramMessage], bot_id: int, system_prompt: str
):
    history = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        role = "assistant" if msg.sender_id == bot_id else "user"
        history.append({"role": role, "content": msg.text})

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
