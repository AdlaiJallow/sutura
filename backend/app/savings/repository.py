import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repository_utils import conditional_update, count_query
from app.savings.models import Savings, SavingsItem


class SavingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_period(self, user_id: uuid.UUID, financial_period_id: uuid.UUID) -> Savings | None:
        stmt = select(Savings).where(
            Savings.user_id == user_id, Savings.financial_period_id == financial_period_id
        )
        return self.db.execute(stmt).scalar_one_or_none()


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
