from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from enum import Enum


class SexEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    sub = Column(String, unique=True, nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    role = Column(String)

    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String, nullable=False)

    sentiments = relationship(
        "SentimentRecord", back_populates="user", cascade="all, delete-orphan"
    )


class SentimentRecord(Base):
    __tablename__ = "sentiments"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, index=True, nullable=False)
    start_state = Column(Integer, nullable=False)
    end_state = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="sentiments")
