from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import EmailVerificationToken, PasswordResetToken, RefreshToken


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- refresh tokens ---
    def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        self.db.add(token)
        self.db.flush()

    # --- email verification tokens ---
    def add_verification_token(self, token: EmailVerificationToken) -> EmailVerificationToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_verification_token_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # --- password reset tokens ---
    def add_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_reset_token_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()
