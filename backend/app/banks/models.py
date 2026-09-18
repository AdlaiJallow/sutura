import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, Money, TimestampMixin, UUIDPKMixin


class BankAccount(UUIDPKMixin, TimestampMixin, Base):
    """spec §17. `account_identifier_encrypted` is never returned in full by any API response —
    only `account_identifier_last4` is used for masked display (§34/§17)."""

    __tablename__ = "bank_accounts"
    __table_args__ = (
        Index("ix_bank_account_user_active", "user_id", "is_active"),
        CheckConstraint(
            "account_type IN ('BANK','MOBILE_MONEY','CASH','SAVINGS','INVESTMENT','OTHER')",
            name="ck_bank_account_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    account_identifier_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    account_identifier_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GMD")
    opening_balance: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    current_balance: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
