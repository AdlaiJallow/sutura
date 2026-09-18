from sqlalchemy.orm import Session

from app.common.errors import UnauthorizedError, ValidationAppError
from app.common.security import hash_password, verify_password
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import ChangePasswordRequest, UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def update_profile(self, user: User, payload: UserUpdate) -> User:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.default_currency is not None:
            if len(payload.default_currency) != 3:
                raise ValidationAppError("default_currency must be a 3-letter ISO 4217 code.")
            user.default_currency = payload.default_currency.upper()
        self.repo.save(user)
        self.db.commit()
        return user

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not user.hashed_password or not verify_password(
            payload.current_password, user.hashed_password
        ):
            raise UnauthorizedError("Current password is incorrect.")
        user.hashed_password = hash_password(payload.new_password)
        self.repo.save(user)
        self.db.commit()

    def deactivate(self, user: User, password: str) -> None:
        if not user.hashed_password or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Password is incorrect.")
        user.is_active = False
        self.repo.save(user)
        self.db.commit()
