from pydantic import BaseModel
from typing import Optional


class SentimentRequest(BaseModel):
    conversation_id: str
    messages: list[str]
    user_id: int


class SentimentResult(BaseModel):
    conversation_id: str
    start_state: int
    end_state: Optional[int] = None
    user_id: int

    model_config = {"from_attributes": True}
