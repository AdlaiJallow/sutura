import uuid

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base, Percentage, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class DistributionRule(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """spec §10. Retired rules are never hard-deleted while any period references them (D-016)."""

    __tablename__ = "distribution_rules"
    __table_args__ = (
        Index(
            "ux_distribution_rules_user_default",
            "user_id",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    categories: Mapped[list["DistributionCategory"]] = relationship(
        back_populates="distribution_rule", cascade="all, delete-orphan"
    )


class DistributionCategory(UUIDPKMixin, TimestampMixin, Base):
    """spec §10/§12. `Category Used` = SUM(Expense.amount WHERE distribution_category_id = X),
    never a separate ledger (D-006)."""

    __tablename__ = "distribution_categories"
    __table_args__ = (
        UniqueConstraint("distribution_rule_id", "name", name="ux_distribution_category_rule_name"),
        Index(
            "ux_distribution_category_unallocated_bucket",
            "distribution_rule_id",
            unique=True,
            postgresql_where=text("is_unallocated_bucket = true"),
        ),
    )

    distribution_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_rules.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    percentage: Mapped[object] = mapped_column(Percentage, nullable=False)
    contributes_to_automatic_savings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    is_unallocated_bucket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    distribution_rule: Mapped["DistributionRule"] = relationship(back_populates="categories")
