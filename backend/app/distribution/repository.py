import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.common.repository_utils import count_query
from app.distribution.models import DistributionCategory, DistributionRule


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
