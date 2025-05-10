from fastapi import APIRouter, Query
from chatbot_app.schemas.message_schema import MessageHistoryResponse
from chatbot_app.services.message_service import fetch_message_history

message_router = APIRouter()


@message_router.get("/history", response_model=MessageHistoryResponse)
async def get_message_history(
    user_id: int = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset_id: int = Query(default=0),
):
    return await fetch_message_history(
        user_id=user_id, limit=limit, offset_id=offset_id
    )
