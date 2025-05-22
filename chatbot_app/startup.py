from dotenv import load_dotenv
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv(dotenv_path="../.env.dev")


def get_env_variable(name: str, cast_type=str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} is not set in environment variables.")
    try:
        return cast_type(value)
    except ValueError:
        raise ValueError(f"{name} must be of type {cast_type.__name__}")


SECRET_KEY = get_env_variable("SECRET_KEY")
ALGORITHM = get_env_variable("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = get_env_variable("ACCESS_TOKEN_EXPIRE_MINUTES", int)
CONNECTION_STRING = get_env_variable("CONNECTION_STRING")
API_ID = get_env_variable("API_ID")
API_HASH = get_env_variable("API_HASH")
SESSION_STRING = get_env_variable("SESSION_STRING")
PHONE_NUMBER = get_env_variable("PHONE_NUMBER")
AI_API_KEY = get_env_variable("AI_API_KEY")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
