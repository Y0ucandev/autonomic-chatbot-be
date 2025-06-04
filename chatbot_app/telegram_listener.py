import asyncio
import logging
from datetime import datetime, timezone
from telethon import events
from chatbot_app.schemas.message_schema import TelegramMessage
from chatbot_app.startup import client
from chatbot_app.services.message_service import (
    generate_ai_response,
    create_private_channel,
    generate_anon_id,
    delete_channel_if_inactive,
    channels_last_message,
    anon_channels_metadata,
)

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

    sender = event.sender_id
    anon_id = f"anon_{message.chat_id}"
    me = await client.get_me()

    if sender:
        response = await generate_ai_response(message.chat_id, me.id)

        await client.send_message(sender, response)
    else:
        if anon_id in anon_channels_metadata:
            channel_id = anon_channels_metadata[anon_id]["channel_id"]
            anon_channels_metadata[anon_id]["last_active"] = datetime.now(timezone.utc)
            channels_last_message[channel_id] = datetime.now(timezone.utc)
        else:
            anon_id = generate_anon_id()
            channel = await create_private_channel(
                f"AnonUser-{anon_id}", "Channel for anonymous user"
            )
            anon_channels_metadata[anon_id] = {
                "channel_id": channel.id,
                "last_active": datetime.now(timezone.utc),
            }
            channels_last_message[channel.id] = datetime.now(timezone.utc)
            logger.info(f"Channel created {channel.id} for anonymous user {anon_id}")

            await client.send_message(channel.id, f"Anonymous user: {msg.message}")
            response = await generate_ai_response(channel.id, me.id)

            await client.send_message(channel.id, response)
            asyncio.create_task(delete_channel_if_inactive(client, channel.id))


async def main():
    logger.info("I'm starting to listen for messages...")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
