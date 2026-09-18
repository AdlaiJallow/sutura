import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, Money, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Income(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """spec §8. Excludes SALARY/ALLOWANCE (D-007) — those live in their own tables only."""

    __tablename__ = "income"
    __table_args__ = (
        Index("ix_income_user_period", "user_id", "financial_period_id"),
        Index("ix_income_type", "income_type"),
        CheckConstraint("amount >= 0", name="ck_income_amount_nonneg"),
        CheckConstraint(
            "income_type IN ('IN_COUNTRY_PAYMENT','PER_DIEM','FREELANCE','BUSINESS',"
            "'INVESTMENT','OTHER')",
            name="ck_income_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    income_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date_received: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurring_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_templates.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
