import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, Money, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Expense(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """spec §9; also serves §12's "distribution category items" (D-006) — no separate
    DistributionItem table. `expense_category` is a second, independent taxonomy from
    `distribution_category_id` (D-006)."""

    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expense_user_period", "user_id", "financial_period_id"),
        Index("ix_expense_distribution_category", "distribution_category_id"),
        Index("ix_expense_user_category", "user_id", "expense_category"),
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        CheckConstraint(
            "expense_category IN ('RENT','FOOD','TRANSPORTATION','ELECTRICITY','WATER',"
            "'INTERNET','PHONE','EDUCATION','HEALTHCARE','FAMILY_SUPPORT','ENTERTAINMENT',"
            "'SHOPPING','DEBT_REPAYMENT','OTHER')",
            name="ck_expense_category",
        ),
        CheckConstraint(
            "payment_method IN ('CASH','BANK_TRANSFER','CARD','MOBILE_MONEY','OTHER')",
            name="ck_expense_payment_method",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    distribution_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    expense_category: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurring_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_templates.id"), nullable=True
    )
