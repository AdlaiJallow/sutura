import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, CreatedAtOnlyMixin, Money, UUIDPKMixin


class BankTransaction(UUIDPKMixin, CreatedAtOnlyMixin, Base):
    """spec §18 — append-only ledger (D-016). No `updated_at`, no soft delete, no UPDATE path.
    Corrections are new ADJUSTMENT rows referencing the original via `related_record_id`."""

    __tablename__ = "bank_transactions"
    __table_args__ = (
        Index("ix_bank_txn_account_date", "bank_account_id", "transaction_date"),
        Index("ix_bank_txn_period", "financial_period_id"),
        CheckConstraint("amount > 0", name="ck_bank_txn_amount_positive"),
        CheckConstraint(
            "transaction_type IN ('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT','ADJUSTMENT')",
            name="ck_bank_txn_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(15), nullable=False)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_record_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    related_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    transfer_pair_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
