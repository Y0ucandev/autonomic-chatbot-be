from sqlalchemy.orm import Session
from chatbot_app.db.models import User as Model_User
from chatbot_app.schemas.users_schema import UserRegister, UserRole
from chatbot_app.services.user_service import hash_password
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException


def create_user(db: Session, user_data: UserRegister, role: UserRole) -> Model_User:
    hashed_password = hash_password(user_data.password)
    db_user = Model_User(
        sub=str(uuid4()),
        email=user_data.email,
        hashed_password=hashed_password,
        role=role,
        name=user_data.name,
        age=user_data.age,
        gender=user_data.gender,
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Registration failed. The email may already be in use or the data is invalid.",
        )
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(Model_User).filter(Model_User.email == email).first()


def clear_users(db):
    db.query(Model_User).delete()
    db.commit()
