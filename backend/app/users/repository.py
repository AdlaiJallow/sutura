import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, email: str, hashed_password: str, full_name: str | None) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
