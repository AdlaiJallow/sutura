import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.common.repository_utils import count_query
from app.distribution.models import DistributionCategory, DistributionRule
from app.expenses.models import Expense
from app.financial_periods.models import FinancialPeriod


class DistributionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_rule(self, rule: DistributionRule) -> DistributionRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def add_category(self, category: DistributionCategory) -> DistributionCategory:
        self.db.add(category)
        self.db.flush()
        return category

    def get_rule(self, user_id: uuid.UUID, rule_id: uuid.UUID) -> DistributionRule | None:
        stmt = (
            select(DistributionRule)
            .options(selectinload(DistributionRule.categories))
            .where(
                DistributionRule.id == rule_id,
                DistributionRule.user_id == user_id,
                DistributionRule.deleted_at.is_(None),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_rules(
        self, user_id: uuid.UUID, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[DistributionRule], int]:
        stmt = (
            select(DistributionRule)
            .options(selectinload(DistributionRule.categories))
            .where(DistributionRule.user_id == user_id, DistributionRule.deleted_at.is_(None))
        )
        if is_active is not None:
            stmt = stmt.where(DistributionRule.is_active == is_active)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(DistributionRule.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def lock_rule_for_update(
        self, user_id: uuid.UUID, rule_id: uuid.UUID
    ) -> DistributionRule | None:
        """SELECT ... FOR UPDATE on the parent rule (D-009): held for the duration of any
        category mutation + resum, so two concurrent edits to the same rule's categories can't
        both validate against a stale sum — the second waits for the first's transaction to
        commit, then re-reads the now-current state."""
        stmt = (
            select(DistributionRule)
            .where(
                DistributionRule.id == rule_id,
                DistributionRule.user_id == user_id,
                DistributionRule.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def unset_other_defaults(self, user_id: uuid.UUID, except_rule_id: uuid.UUID) -> None:
        """Clears `is_default` on every other rule for this user before the caller sets the new
        default — unset-then-set inside one transaction avoids ever tripping the partial unique
        index `ux_distribution_rules_user_default` (D-009/D-010-style handling)."""
        self.db.execute(
            update(DistributionRule)
            .where(
                DistributionRule.user_id == user_id,
                DistributionRule.is_default.is_(True),
                DistributionRule.id != except_rule_id,
            )
            .values(is_default=False)
        )

    def save_rule(self, rule: DistributionRule) -> DistributionRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def list_categories(self, rule_id: uuid.UUID) -> list[DistributionCategory]:
        stmt = (
            select(DistributionCategory)
            .where(DistributionCategory.distribution_rule_id == rule_id)
            .order_by(DistributionCategory.display_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    def save_category(self, category: DistributionCategory) -> DistributionCategory:
        self.db.add(category)
        self.db.flush()
        return category

    def delete_category(self, category: DistributionCategory) -> None:
        self.db.delete(category)
        self.db.flush()

    def reset_unallocated_flags(self, rule_id: uuid.UUID) -> None:
        """Clears every category's `is_unallocated_bucket` for this rule before applying the
        new set, so moving the flag from one category to another never trips the partial
        unique index `ux_distribution_category_unallocated_bucket` mid-transaction (D-010)."""
        self.db.execute(
            update(DistributionCategory)
            .where(DistributionCategory.distribution_rule_id == rule_id)
            .values(is_unallocated_bucket=False)
        )

    def is_category_referenced_by_expenses(self, category_id: uuid.UUID) -> bool:
        stmt = (
            select(Expense.id)
            .where(
                Expense.distribution_category_id == category_id,
                Expense.deleted_at.is_(None),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def is_rule_selected_by_open_period(self, user_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        stmt = (
            select(FinancialPeriod.id)
            .where(
                FinancialPeriod.user_id == user_id,
                FinancialPeriod.distribution_rule_id == rule_id,
                FinancialPeriod.status == "OPEN",
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None
