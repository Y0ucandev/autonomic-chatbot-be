from fastapi import APIRouter, Query, HTTPException, Depends
from chatbot_app.schemas.message_schema import MessageHistoryResponse, MessageIn
from chatbot_app.services.message_service import (
    fetch_message_history,
    generate_ai_response,
    extract_direction_and_user_id,
    add_user_facts,
)
from chatbot_app.startup import client, OPERATOR_CHAT_ID
from sqlalchemy.orm import Session
from chatbot_app.db.database import SessionLocal
import logging
from chatbot_app.db.models import FactRecord, User

logger = logging.getLogger(__name__)
message_router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@message_router.get("/history", response_model=MessageHistoryResponse)
async def get_message_history(
    user_id: int = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset_id: int = Query(default=0),
):
    TELEGRAM_CHAT_ID = int(OPERATOR_CHAT_ID)

    full_history = await fetch_message_history(
        chat_id=TELEGRAM_CHAT_ID, limit=limit, offset_id=offset_id
    )

    filtered_messages = []
    for msg in full_history.messages:
        if not msg.text:
            continue

        extracted = extract_direction_and_user_id(msg.text)
        if not extracted:
            continue

        direction, extracted_id = extracted

        if extracted_id == str(user_id):
            clean_text = msg.text.split("]", 1)[1].strip()
            msg.text = clean_text
            filtered_messages.append(msg)

    return MessageHistoryResponse(
        messages=filtered_messages,
        next_offset_id=full_history.next_offset_id,
    )


@message_router.post("/send-message")
async def send_message(payload: MessageIn, db: Session = Depends(get_db)):
    try:
        if not client.is_connected():
            logger.error("Client is not connected")
            raise HTTPException(status_code=503, detail="Client connection failed")

        existing_user = db.query(User).filter_by(id=payload.user_id).first()
        if not existing_user:
            fake_email = f"anonim_{payload.user_id}@notrealemail.local"
            db.add(
                User(
                    id=payload.user_id,
                    email=fake_email,
                    name="Anonim User",
                    gender="other",
                )
            )
            db.commit()

        full_message = f"[from {payload.user_id}] {payload.message}"
        await client.send_message(int(OPERATOR_CHAT_ID), full_message)

        response = await generate_ai_response(payload.user_id)

        await client.send_message(int(OPERATOR_CHAT_ID), response)
        await add_user_facts(payload.user_id, payload.message, db)
        db.commit()
        return {"status": "ok"}

    except ValueError as ve:
        logger.error(f"Value error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except ConnectionError as ce:
        logger.error(f"Connection error: {ce}")
        raise HTTPException(status_code=503, detail="Client connection failed")

    except Exception:
        logger.exception("Unexpected error occurred")
        raise HTTPException(status_code=500, detail="Internal server error")

        
@message_router.get("/search", response_model=MessageHistoryResponse)
async def search_messages(
    user_id: int = Query(...),
    query: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset_id: int = Query(default=0),
):
    try:
        TELEGRAM_CHAT_ID = int(OPERATOR_CHAT_ID)

        full_history = await fetch_message_history(
            chat_id=TELEGRAM_CHAT_ID, limit=100, offset_id=offset_id
        )

        matching_messages = []
        for msg in full_history.messages:
            if not msg.text:
                continue

            extracted = extract_direction_and_user_id(msg.text)
            if not extracted:
                continue

            direction, extracted_id = extracted
            if extracted_id != str(user_id):
                continue

            clean_text = msg.text.split("]", 1)[1].strip()

            if query.lower() in clean_text.lower():
                msg.text = clean_text
                matching_messages.append(msg)

            if len(matching_messages) >= limit:
                break

        return MessageHistoryResponse(
            messages=matching_messages, next_offset_id=full_history.next_offset_id
        )

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        logger.exception("Unexpected error during search")
        raise HTTPException(
            status_code=500, detail="Internal server error during message search."
        )


@message_router.get("/user-facts/{user_id}")
async def get_user_facts(user_id: int, db: Session = Depends(get_db)):
    try:
        facts = db.query(FactRecord).filter_by(user_id=user_id).all()
    except Exception:
        raise HTTPException(status_code=500, detail="Database query failed")

    if not facts:
        return []

    return [fact.user_fact for fact in facts]
