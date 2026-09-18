import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repository_utils import conditional_update, count_query
from app.salary.models import Salary


class SalaryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, salary: Salary) -> Salary:
        self.db.add(salary)
        self.db.flush()
        return salary

    def get_owned(self, user_id: uuid.UUID, salary_id: uuid.UUID) -> Salary | None:
        stmt = select(Salary).where(
            Salary.id == salary_id, Salary.user_id == user_id, Salary.deleted_at.is_(None)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_for_period(self, user_id: uuid.UUID, financial_period_id: uuid.UUID) -> Salary | None:
        stmt = select(Salary).where(
            Salary.user_id == user_id,
            Salary.financial_period_id == financial_period_id,
            Salary.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_period(
        self, user_id: uuid.UUID, financial_period_id: uuid.UUID | None, *, page: int, page_size: int
    ) -> tuple[list[Salary], int]:
        stmt = select(Salary).where(Salary.user_id == user_id, Salary.deleted_at.is_(None))
        if financial_period_id is not None:
            stmt = stmt.where(Salary.financial_period_id == financial_period_id)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(Salary.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def update_owned(
        self,
        user_id: uuid.UUID,
        salary_id: uuid.UUID,
        expected_updated_at: datetime,
        values: dict,
    ) -> int:
        return conditional_update(
            self.db,
            Salary,
            record_id=salary_id,
            user_id=user_id,
            expected_updated_at=expected_updated_at,
            values=values,
        )

    def soft_delete(self, salary: Salary) -> None:
        from datetime import datetime, timezone

        salary.deleted_at = datetime.now(timezone.utc)
        self.db.add(salary)
        self.db.flush()
