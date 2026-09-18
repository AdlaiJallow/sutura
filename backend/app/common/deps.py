"""Shared FastAPI dependencies: DB session and the authenticated-user dependency every
other router uses to scope queries by user_id (never trust an id in the path alone).
"""
import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.errors import UnauthorizedError
from app.common.security import TokenType, decode_token
from app.users.models import User
from app.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing or invalid Authorization header.")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Invalid or expired access token.")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    return user
