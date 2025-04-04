from dotenv import load_dotenv
import os

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
