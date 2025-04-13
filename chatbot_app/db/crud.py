from sqlalchemy.orm import Session
from chatbot_app.db.models import User
from chatbot_app.services.user_service import hash_password


def create_user(db: Session, sub: str, email: str, password: str, role: str):
    hashed_password = hash_password(password)
    db_user = User(sub=sub, email=email, hashed_password=hashed_password, role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def clear_users(db):
    db.query(User).delete()
    db.commit()
