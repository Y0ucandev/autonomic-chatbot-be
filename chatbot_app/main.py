from telethon import events
import asyncio
import logging
from fastapi import FastAPI
from chatbot_app.api.routers.user_router import user_router
from chatbot_app.api.routers.message_router import message_router
from chatbot_app.api.routers.analysis_router import analysis_router
from chatbot_app.db.database import Base, engine
from chatbot_app.db.models import User
from contextlib import asynccontextmanager
from chatbot_app.startup import client, OPERATOR_CHAT_ID
from chatbot_app.services.message_service import (
    generate_ai_response,
    add_user_facts,
    shrink_id,
)
from chatbot_app.db.database import SessionLocal

logger = logging.getLogger(__name__)


@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    session = SessionLocal()
    logger.info("I'm starting to listen for messages...")
    msg = event.message
    me = await client.get_me()

    if msg.sender_id == me.id:
        return

    user_id = shrink_id(int(msg.sender_id))
    chat_id = msg.chat_id
    try:
        existing_user = session.query(User).filter_by(id=user_id).first()
        if not existing_user:
            fake_email = f"telegram_{user_id}@notrealemail.local"
            session.add(
                User(id=user_id, email=fake_email, name="Telegram User", gender="other")
            )
            session.commit()

        logger.info("New message from user_id %s: %s", user_id, msg.text or "")

        full_message = f"[from {user_id}] {msg.text or ''}"

        await client.send_message(int(OPERATOR_CHAT_ID), full_message)

        raw_response = await generate_ai_response(user_id)

        await client.send_message(int(OPERATOR_CHAT_ID), raw_response)
        await add_user_facts(user_id, msg.text, session)
        session.commit()
        response_text = (
            raw_response.split("]", 1)[1].strip()
            if "]" in raw_response
            else raw_response
        )

        await client.send_message(chat_id, response_text)

    except Exception as e:
        logger.error(f"Failed to handle message: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app):
    if not client.is_connected():
        await client.start()
    logger.info("Test send_message")
    await client.send_message("me", "✅ Client started and ready.")
    asyncio.create_task(client.run_until_disconnected())
    yield


app = FastAPI(lifespan=lifespan)


Base.metadata.create_all(bind=engine)

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(message_router, prefix="/message", tags=["message"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
