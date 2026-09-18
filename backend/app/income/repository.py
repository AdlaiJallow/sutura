import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repository_utils import count_query
from app.income.models import Income


class IncomeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, income: Income) -> Income:
        self.db.add(income)
        self.db.flush()
        return income

    def get_owned(self, user_id: uuid.UUID, income_id: uuid.UUID) -> Income | None:
        stmt = select(Income).where(
            Income.id == income_id, Income.user_id == user_id, Income.deleted_at.is_(None)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        user_id: uuid.UUID,
        *,
        financial_period_id: uuid.UUID | None,
        income_type: str | None,
        date_from,
        date_to,
        page: int,
        page_size: int,
    ) -> tuple[list[Income], int]:
        stmt = select(Income).where(Income.user_id == user_id, Income.deleted_at.is_(None))
        if financial_period_id is not None:
            stmt = stmt.where(Income.financial_period_id == financial_period_id)
        if income_type is not None:
            stmt = stmt.where(Income.income_type == income_type)
        if date_from is not None:
            stmt = stmt.where(Income.date_received >= date_from)
        if date_to is not None:
            stmt = stmt.where(Income.date_received <= date_to)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(Income.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def soft_delete(self, income: Income) -> None:
        income.deleted_at = datetime.now(timezone.utc)
        self.db.add(income)
        self.db.flush()
