from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class TelegramMessage(BaseModel):
    id: int
    sender_id: int
    chat_id: int
    text: Optional[str] = None
    media_path: Optional[str] = None
    date: datetime


class MessageHistoryResponse(BaseModel):
    messages: List[TelegramMessage]
    next_offset_id: Optional[int] = None
