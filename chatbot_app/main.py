from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Welcome"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
