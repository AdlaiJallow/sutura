import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, CreatedAtOnlyMixin, Money, TimestampMixin, UUIDPKMixin


class FinancialPeriod(UUIDPKMixin, TimestampMixin, Base):
    """spec §5 — everything hangs off this. Whole calendar month only in v1 (D-017)."""

    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="ux_financial_period_user_year_month"),
        Index("ix_financial_period_user_status", "user_id", "status"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_financial_period_month_range"),
        CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_financial_period_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN")
    distribution_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_rules.id"), nullable=True
    )
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GMD")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reopened_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    last_reopened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RecurringTemplate(UUIDPKMixin, TimestampMixin, Base):
    """D-003 — recurring intent, never a mutable shared row. Editing a template never touches
    already-generated per-period rows."""

    __tablename__ = "recurring_templates"
    __table_args__ = (
        Index("ix_recurring_template_user_active", "user_id", "is_active"),
        CheckConstraint(
            "record_type IN ('SALARY','ALLOWANCE','INCOME','EXPENSE')",
            name="ck_recurring_template_record_type",
        ),
        CheckConstraint("frequency = 'MONTHLY'", name="ck_recurring_template_frequency_v1"),
        CheckConstraint("amount >= 0", name="ck_recurring_template_amount_nonneg"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False, default="MONTHLY")
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    start_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=True
    )
    end_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MonthlyFinancialSummary(UUIDPKMixin, CreatedAtOnlyMixin, Base):
    """spec §22/§23, D-004 — versioned, append-only snapshot. Old versions are never updated
    or deleted; only `is_current` moves to the newest version on re-close after a reopen."""

    __tablename__ = "monthly_financial_summaries"
    __table_args__ = (
        UniqueConstraint(
            "financial_period_id", "version", name="ux_monthly_summary_period_version"
        ),
        Index(
            "ux_monthly_summary_current",
            "financial_period_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        CheckConstraint(
            "triggered_by IN ('CLOSE','REOPEN_RECALC','MANUAL_REFRESH')",
            name="ck_monthly_summary_triggered_by",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    total_salary_income: Mapped[object] = mapped_column(Money, nullable=False)
    total_allowances: Mapped[object] = mapped_column(Money, nullable=False)
    total_other_income: Mapped[object] = mapped_column(Money, nullable=False)
    total_monthly_income: Mapped[object] = mapped_column(Money, nullable=False)
    total_expenses: Mapped[object] = mapped_column(Money, nullable=False)
    total_planned_savings: Mapped[object] = mapped_column(Money, nullable=False)
    automatic_savings: Mapped[object] = mapped_column(Money, nullable=False)
    manual_savings: Mapped[object] = mapped_column(Money, nullable=False)
    final_savings: Mapped[object] = mapped_column(Money, nullable=False)
    total_bank_deposits: Mapped[object] = mapped_column(Money, nullable=False)
    undistributed_savings: Mapped[object] = mapped_column(Money, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(10), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
