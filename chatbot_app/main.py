import logging
from fastapi import FastAPI
from chatbot_app.api.routers.user_router import user_router
from chatbot_app.api.routers.message_router import message_router
from chatbot_app.api.routers.analysis_router import analysis_router
from chatbot_app.db.database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(message_router, prefix="/message", tags=["message"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
