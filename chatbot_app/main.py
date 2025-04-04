from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from chatbot_app.startup import CONNECTION_STRING
from chatbot_app.api.routers.user_router import user_router
from chatbot_app.api.routers.message_router import message_router


app = FastAPI()

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(message_router, prefix="/message", tags=["message"])

engine = create_engine(CONNECTION_STRING, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_model=dict)
async def read_root() -> dict:
    return {"message": "Welcome"}


@app.get("/items/")
async def read_items(db: Session = Depends(get_db)) -> dict:
    return {"message": "Async DB session initialized"}


@app.get("/items/{item_id}", response_model=dict)
async def read_item(item_id: int, q: str = None) -> dict:
    return {"item_id": item_id, "q": q}
