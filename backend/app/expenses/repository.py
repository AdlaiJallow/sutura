import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repository_utils import conditional_update, count_query
from app.expenses.models import Expense


class ExpenseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, expense: Expense) -> Expense:
        self.db.add(expense)
        self.db.flush()
        return expense

    def get_owned(self, user_id: uuid.UUID, expense_id: uuid.UUID) -> Expense | None:
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.user_id == user_id, Expense.deleted_at.is_(None)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        user_id: uuid.UUID,
        *,
        financial_period_id: uuid.UUID | None,
        distribution_category_id: uuid.UUID | None,
        expense_category: str | None,
        payment_method: str | None,
        date_from,
        date_to,
        page: int,
        page_size: int,
    ) -> tuple[list[Expense], int]:
        stmt = select(Expense).where(Expense.user_id == user_id, Expense.deleted_at.is_(None))
        if financial_period_id is not None:
            stmt = stmt.where(Expense.financial_period_id == financial_period_id)
        if distribution_category_id is not None:
            stmt = stmt.where(Expense.distribution_category_id == distribution_category_id)
        if expense_category is not None:
            stmt = stmt.where(Expense.expense_category == expense_category)
        if payment_method is not None:
            stmt = stmt.where(Expense.payment_method == payment_method)
        if date_from is not None:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Expense.expense_date <= date_to)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(Expense.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def update_owned(
        self,
        user_id: uuid.UUID,
        expense_id: uuid.UUID,
        expected_updated_at: datetime,
        values: dict,
    ) -> int:
        return conditional_update(
            self.db,
            Expense,
            record_id=expense_id,
            user_id=user_id,
            expected_updated_at=expected_updated_at,
            values=values,
        )

    def soft_delete(self, expense: Expense) -> None:
        expense.deleted_at = datetime.now(timezone.utc)
        self.db.add(expense)
        self.db.flush()
