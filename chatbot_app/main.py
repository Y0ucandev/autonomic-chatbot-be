from fastapi import FastAPI
from chatbot_app.api.routers.user_router import user_router
from chatbot_app.api.routers.message_router import message_router


app = FastAPI()

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(message_router, prefix="/message", tags=["message"])
