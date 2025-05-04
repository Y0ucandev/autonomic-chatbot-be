import asyncio
import logging
from telethon.sync import TelegramClient
from startup import API_ID, API_HASH, PHONE_NUMBER
from telethon.sessions import StringSession

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(), API_ID, API_HASH)


async def login():
    await client.start(PHONE_NUMBER)
    logger.info("Login success!")
    logger.info(client.session.save())
    await client.disconnect()


asyncio.run(login())
