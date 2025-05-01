import asyncio
import logging
from telethon import events
from chatbot_app.schemas.message_schema import TelegramMessage
from chatbot_app.startup import client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@client.on(events.NewMessage)
async def handle_new_message(event):
    msg = event.message
    message = TelegramMessage(
        id=msg.id,
        sender_id=msg.sender_id or 0,
        chat_id=msg.chat_id or 0,
        text=msg.message or "",
        date=msg.date,
    )

    logger.info("New message:\n%s", message.model_dump_json(indent=2))


async def main():
    logger.info("I'm starting to listen for messages...")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
