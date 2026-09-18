import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base, Money, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Salary(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """spec §6. Exactly one Salary row per user per period (D-008)."""

    __tablename__ = "salaries"
    __table_args__ = (
        UniqueConstraint("user_id", "financial_period_id", name="ux_salary_user_period"),
        CheckConstraint("net_amount >= 0", name="ck_salary_net_amount_nonneg"),
        CheckConstraint("status IN ('EXPECTED','RECEIVED')", name="ck_salary_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    net_amount: Mapped[object] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="RECEIVED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_templates.id"), nullable=True
    )
    is_recurring_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
