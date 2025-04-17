from sqlalchemy import Column, Integer, String
from .database import Base
from enum import Enum


class SexEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String, unique=True, nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    role = Column(String)

    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String, nullable=False)
