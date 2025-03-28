from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env.dev")


def get_connection_string():
    return os.getenv("CONNECTION_STRING")