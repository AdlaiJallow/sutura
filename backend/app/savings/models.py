import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, Money, Percentage, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Savings(UUIDPKMixin, TimestampMixin, Base):
    """spec §15/§28 — per-period cached rollup (D-012), recalculated from source records."""

    __tablename__ = "savings"
    __table_args__ = (
        UniqueConstraint("financial_period_id", name="ux_savings_period"),
        CheckConstraint("undistributed_total >= 0", name="ck_savings_undistributed_nonneg"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False
    )
    automatic_savings_computed: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    manual_savings_total: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    final_savings_total: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    distributed_total: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    undistributed_total: Mapped[object] = mapped_column(Money, nullable=False, default=0)
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavingsItem(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """spec §16 — manual savings entries; the only stored manual-entry source table (D-012)."""

    __tablename__ = "savings_items"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_savings_item_amount_positive"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    savings_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("savings.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    destination: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SavingsDistributionRule(UUIDPKMixin, TimestampMixin, Base):
    """D-013 — parallel to income DistributionRule, but for splitting savings across banks."""

    __tablename__ = "savings_distribution_rules"
    __table_args__ = (
        Index(
            "ux_savings_dist_rule_user_default",
            "user_id",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SavingsDistributionRuleItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "savings_distribution_rule_items"
    __table_args__ = (
        CheckConstraint(
            "bank_account_id IS NOT NULL OR destination_label IS NOT NULL",
            name="ck_savings_dist_rule_item_destination",
        ),
    )

    savings_distribution_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("savings_distribution_rules.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=True
    )
    destination_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    percentage: Mapped[object] = mapped_column(Percentage, nullable=False)


class SavingsAllocation(UUIDPKMixin, TimestampMixin, Base):
    """spec §19/§20/§28 (D-014). Service layer must guarantee
    SUM(amount) FOR savings_id <= Savings.final_savings_total (never over-allocate)."""

    __tablename__ = "savings_allocations"
    __table_args__ = (
        CheckConstraint(
            "bank_account_id IS NOT NULL OR destination_label IS NOT NULL",
            name="ck_savings_allocation_destination",
        ),
        CheckConstraint("amount > 0", name="ck_savings_allocation_amount_positive"),
        CheckConstraint(
            "allocation_method IN ('AUTO','MANUAL')", name="ck_savings_allocation_method"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    savings_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("savings.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=True
    )
    destination_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    amount: Mapped[object] = mapped_column(Money, nullable=False)
    allocation_method: Mapped[str] = mapped_column(String(10), nullable=False)
    bank_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_transactions.id"), nullable=True
    )
