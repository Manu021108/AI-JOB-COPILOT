from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest

def normalize_email(email: str) -> str:
    return email.strip().lower()

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))

def create_user(db: Session, payload: RegisterRequest) -> User:
    user = User(name=payload.name.strip(), email=normalize_email(payload.email), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    return user if user and user.is_active and verify_password(password, user.password_hash) else None
