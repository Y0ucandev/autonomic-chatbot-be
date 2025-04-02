from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env.dev")


def get_connection_string():
    return os.getenv("CONNECTION_STRING")


SECRET_KEY=os.getenv("SECRET_KEY")
ALGORITHM=os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
