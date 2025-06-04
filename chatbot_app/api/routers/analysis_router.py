from chatbot_app.schemas.analysis_schema import SentimentResult, SentimentRequest
from chatbot_app.services.analysis_service import analyze_sentiment
from chatbot_app.db.models import SentimentRecord
from sqlalchemy.orm import Session
from chatbot_app.db.database import SessionLocal
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

analysis_router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@analysis_router.post("/sentiment", response_model=SentimentResult)
async def save_sentiment(payload: SentimentRequest, db: Session = Depends(get_db)):
    if len(payload.messages) < 3:
        raise HTTPException(status_code=400, detail="At least 3 messages are needed")

    start_score = await analyze_sentiment(payload.messages[:3])
    end_score = await analyze_sentiment(payload.messages[-3:])

    record = SentimentRecord(
        conversation_id=payload.conversation_id,
        start_state=start_score,
        end_state=end_score,
        user_id=payload.user_id,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@analysis_router.get(
    "/sentiment/{conversation_id}", response_model=List[SentimentResult]
)
def get_sentiment(conversation_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(SentimentRecord).where(
        SentimentRecord.conversation_id == conversation_id
    )
    result = db.execute(stmt)
    records = result.scalars().all()

    if not records:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return records
