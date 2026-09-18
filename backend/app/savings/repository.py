import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.common.repository_utils import conditional_update, count_query
from app.savings.models import (
    Savings,
    SavingsAllocation,
    SavingsDistributionRule,
    SavingsDistributionRuleItem,
    SavingsItem,
)


class SavingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_period(self, user_id: uuid.UUID, financial_period_id: uuid.UUID) -> Savings | None:
        stmt = select(Savings).where(
            Savings.user_id == user_id, Savings.financial_period_id == financial_period_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID, savings_id: uuid.UUID) -> Savings | None:
        stmt = select(Savings).where(Savings.id == savings_id, Savings.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def lock_by_id(self, user_id: uuid.UUID, savings_id: uuid.UUID) -> Savings | None:
        """SELECT ... FOR UPDATE on the `Savings` cache row, held for the duration of an
        allocate-check-insert sequence (D-014/§19): two concurrent allocation requests against
        the same `savings_id` cannot both validate against a stale `SUM(amount)` — the second
        waits for the first's transaction to commit, then re-reads the now-current sum. Same
        pattern as `DistributionRepository.lock_rule_for_update` (D-009)."""
        stmt = (
            select(Savings)
            .where(Savings.id == savings_id, Savings.user_id == user_id)
            .with_for_update()
        )
        return self.db.execute(stmt).scalar_one_or_none()


class SavingsDistributionRuleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_rule(self, rule: SavingsDistributionRule) -> SavingsDistributionRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def add_item(self, item: SavingsDistributionRuleItem) -> SavingsDistributionRuleItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get_rule(
        self, user_id: uuid.UUID, rule_id: uuid.UUID
    ) -> SavingsDistributionRule | None:
        stmt = (
            select(SavingsDistributionRule)
            .options(selectinload(SavingsDistributionRule.items))
            .where(SavingsDistributionRule.id == rule_id, SavingsDistributionRule.user_id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_rules(
        self, user_id: uuid.UUID, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[SavingsDistributionRule], int]:
        stmt = (
            select(SavingsDistributionRule)
            .options(selectinload(SavingsDistributionRule.items))
            .where(SavingsDistributionRule.user_id == user_id)
        )
        if is_active is not None:
            stmt = stmt.where(SavingsDistributionRule.is_active == is_active)
        total = count_query(self.db, stmt)
        stmt = (
            stmt.order_by(SavingsDistributionRule.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def lock_rule_for_update(
        self, user_id: uuid.UUID, rule_id: uuid.UUID
    ) -> SavingsDistributionRule | None:
        """SELECT ... FOR UPDATE on the parent rule (D-009-style, applied to savings rules) —
        held for the duration of any item mutation + resum, closing the same concurrent-edit
        race `DistributionRepository.lock_rule_for_update` closes for income distribution rules."""
        stmt = (
            select(SavingsDistributionRule)
            .where(SavingsDistributionRule.id == rule_id, SavingsDistributionRule.user_id == user_id)
            .with_for_update()
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def unset_other_defaults(self, user_id: uuid.UUID, except_rule_id: uuid.UUID) -> None:
        self.db.execute(
            update(SavingsDistributionRule)
            .where(
                SavingsDistributionRule.user_id == user_id,
                SavingsDistributionRule.is_default.is_(True),
                SavingsDistributionRule.id != except_rule_id,
            )
            .values(is_default=False)
        )

    def save_rule(self, rule: SavingsDistributionRule) -> SavingsDistributionRule:
        self.db.add(rule)
        self.db.flush()
        return rule

    def list_items(self, rule_id: uuid.UUID) -> list[SavingsDistributionRuleItem]:
        stmt = (
            select(SavingsDistributionRuleItem)
            .where(SavingsDistributionRuleItem.savings_distribution_rule_id == rule_id)
            .order_by(SavingsDistributionRuleItem.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def save_item(self, item: SavingsDistributionRuleItem) -> SavingsDistributionRuleItem:
        self.db.add(item)
        self.db.flush()
        return item

    def delete_item(self, item: SavingsDistributionRuleItem) -> None:
        self.db.delete(item)
        self.db.flush()


class SavingsAllocationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, allocation: SavingsAllocation) -> SavingsAllocation:
        self.db.add(allocation)
        self.db.flush()
        return allocation

    def save(self, allocation: SavingsAllocation) -> SavingsAllocation:
        self.db.add(allocation)
        self.db.flush()
        return allocation

    def get_owned(
        self, user_id: uuid.UUID, allocation_id: uuid.UUID
    ) -> SavingsAllocation | None:
        stmt = select(SavingsAllocation).where(
            SavingsAllocation.id == allocation_id, SavingsAllocation.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_savings_id(
        self,
        user_id: uuid.UUID,
        savings_id: uuid.UUID,
        *,
        allocation_method: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SavingsAllocation], int]:
        stmt = select(SavingsAllocation).where(
            SavingsAllocation.user_id == user_id, SavingsAllocation.savings_id == savings_id
        )
        if allocation_method is not None:
            stmt = stmt.where(SavingsAllocation.allocation_method == allocation_method)
        total = count_query(self.db, stmt)
        stmt = (
            stmt.order_by(SavingsAllocation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def sum_amount_for_savings(self, savings_id: uuid.UUID):
        """Must be called only while the parent `Savings` row is held under
        `SavingsRepository.lock_by_id` (D-014) so this sum can't go stale between the check and
        the insert that follows it."""
        stmt = select(func.coalesce(func.sum(SavingsAllocation.amount), 0)).where(
            SavingsAllocation.savings_id == savings_id
        )
        return self.db.execute(stmt).scalar_one()

    def delete(self, allocation: SavingsAllocation) -> None:
        self.db.delete(allocation)
        self.db.flush()

    def delete_auto_for_savings(self, savings_id: uuid.UUID) -> None:
        """Bulk-deletes every AUTO allocation for this `savings_id` (never touches MANUAL rows)
        — the "replace, don't stack" half of `apply_rule`'s documented behavior."""
        self.db.execute(
            delete(SavingsAllocation).where(
                SavingsAllocation.savings_id == savings_id,
                SavingsAllocation.allocation_method == "AUTO",
            )
        )


class SavingsItemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, item: SavingsItem) -> SavingsItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get_owned(self, user_id: uuid.UUID, item_id: uuid.UUID) -> SavingsItem | None:
        stmt = select(SavingsItem).where(
            SavingsItem.id == item_id, SavingsItem.user_id == user_id, SavingsItem.deleted_at.is_(None)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        user_id: uuid.UUID,
        *,
        financial_period_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SavingsItem], int]:
        stmt = select(SavingsItem).where(
            SavingsItem.user_id == user_id, SavingsItem.deleted_at.is_(None)
        )
        if financial_period_id is not None:
            stmt = stmt.where(SavingsItem.financial_period_id == financial_period_id)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(SavingsItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def update_owned(
        self,
        user_id: uuid.UUID,
        item_id: uuid.UUID,
        expected_updated_at: datetime,
        values: dict,
    ) -> int:
        return conditional_update(
            self.db,
            SavingsItem,
            record_id=item_id,
            user_id=user_id,
            expected_updated_at=expected_updated_at,
            values=values,
        )

    def soft_delete(self, item: SavingsItem) -> None:
        item.deleted_at = datetime.now(timezone.utc)
        self.db.add(item)
        self.db.flush()
