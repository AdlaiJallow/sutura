"""Auth business logic: register/login/refresh/logout + email-verification/password-reset flows.

D-020 (cross-user access is 404, never 403) is enforced at the router/service boundary of every
*other* module via get_current_user; this module is the one place that legitimately deals in
credentials, so it has its own careful error handling (never leak whether an email exists on
password-reset requests, never log a raw password/token).
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.models import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.auth.repository import AuthRepository
from app.auth.schemas import RegisterRequest
from app.auth.token_utils import generate_raw_token, hash_token
from app.common.config import get_settings
from app.common.errors import ConflictError, UnauthorizedError, ValidationAppError
from app.common.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.users.models import User
from app.users.repository import UserRepository

logger = logging.getLogger(__name__)
settings = get_settings()

VERIFICATION_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(hours=1)


def _send_email_stub(to: str, subject: str, body: str) -> None:
    """Dev-only stand-in for a real email provider. Never logs secrets in prod; here the token
    itself is intentionally logged because this IS the delivery mechanism for local dev.
    """
    logger.info("EMAIL to=%s subject=%s body=%s", to, subject, body)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.repo = AuthRepository(db)

    def register(self, payload: RegisterRequest) -> User:
        if self.users.get_by_email(payload.email):
            raise ConflictError("An account with this email already exists.")
        user = self.users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        self._issue_verification_token(user)
        self.db.commit()
        return user

    def _issue_verification_token(self, user: User) -> str:
        raw = generate_raw_token()
        token = EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_TTL,
        )
        self.repo.add_verification_token(token)
        _send_email_stub(
            user.email,
            "Verify your Sutura account",
            f"Your verification token is: {raw}",
        )
        return raw

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.users.get_by_email(email)
        if user is None or not user.hashed_password or not verify_password(
            password, user.hashed_password
        ):
            raise UnauthorizedError("Incorrect email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        access = create_access_token(user.id)
        raw_refresh = generate_raw_token()
        refresh_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        self.repo.add_refresh_token(refresh_row)
        self.db.commit()
        return access, raw_refresh

    def refresh(self, raw_refresh_token: str) -> tuple[str, str]:
        """Validate the presented refresh token, then rotate it: issue a brand-new refresh token
        and revoke the old one (D-026). Rotation limits the blast radius of a leaked/stolen
        refresh token to a single use — reuse of a revoked token fails the same way an invalid
        token would.
        """
        token_row = self.repo.get_refresh_token_by_hash(hash_token(raw_refresh_token))
        if token_row is None or token_row.revoked_at is not None:
            raise UnauthorizedError("Invalid refresh token.")
        if token_row.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token has expired.")

        access = create_access_token(token_row.user_id)
        new_raw_refresh = generate_raw_token()
        new_refresh_row = RefreshToken(
            user_id=token_row.user_id,
            token_hash=hash_token(new_raw_refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        self.repo.add_refresh_token(new_refresh_row)
        self.repo.revoke_refresh_token(token_row)
        self.db.commit()
        return access, new_raw_refresh

    def logout(self, raw_refresh_token: str) -> None:
        token_row = self.repo.get_refresh_token_by_hash(hash_token(raw_refresh_token))
        if token_row is not None and token_row.revoked_at is None:
            self.repo.revoke_refresh_token(token_row)
            self.db.commit()

    def resend_verification(self, email: str) -> None:
        user = self.users.get_by_email(email)
        if user is None or user.is_email_verified:
            return  # never reveal whether the account exists or its verification state
        self._issue_verification_token(user)
        self.db.commit()

    def verify_email(self, raw_token: str) -> None:
        token_row = self.repo.get_verification_token_by_hash(hash_token(raw_token))
        if token_row is None or token_row.used_at is not None:
            raise ValidationAppError("Invalid or already-used verification token.")
        if token_row.expires_at < datetime.now(timezone.utc):
            raise ValidationAppError("Verification token has expired.")
        user = self.users.get_by_id(token_row.user_id)
        if user is None:
            raise ValidationAppError("Invalid verification token.")
        user.is_email_verified = True
        token_row.used_at = datetime.now(timezone.utc)
        self.users.save(user)
        self.db.commit()

    def forgot_password(self, email: str) -> None:
        user = self.users.get_by_email(email)
        if user is None:
            return  # never reveal whether the account exists
        raw = generate_raw_token()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + RESET_TOKEN_TTL,
        )
        self.repo.add_reset_token(token)
        _send_email_stub(user.email, "Reset your Sutura password", f"Your reset token is: {raw}")
        self.db.commit()

    def reset_password(self, raw_token: str, new_password: str) -> None:
        token_row = self.repo.get_reset_token_by_hash(hash_token(raw_token))
        if token_row is None or token_row.used_at is not None:
            raise ValidationAppError("Invalid or already-used reset token.")
        if token_row.expires_at < datetime.now(timezone.utc):
            raise ValidationAppError("Reset token has expired.")
        user = self.users.get_by_id(token_row.user_id)
        if user is None:
            raise ValidationAppError("Invalid reset token.")
        user.hashed_password = hash_password(new_password)
        token_row.used_at = datetime.now(timezone.utc)
        self.users.save(user)
        self.db.commit()
