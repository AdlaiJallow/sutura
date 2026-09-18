import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError
from app.expenses.models import Expense
from app.expenses.repository import ExpenseRepository
from app.expenses.schemas import ExpenseCreate
from app.financial_periods.repository import FinancialPeriodRepository
from app.users.models import User


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ExpenseRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: ExpenseCreate) -> Expense:
        self._ensure_period_open(user, payload.financial_period_id)
        expense = Expense(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            distribution_category_id=payload.distribution_category_id,
            name=payload.name,
            expense_category=payload.expense_category,
            amount=payload.amount,
            currency=payload.currency.upper(),
            expense_date=payload.expense_date,
            payment_method=payload.payment_method,
            bank_account_id=payload.bank_account_id,
            notes=payload.notes,
        )
        self.repo.create(expense)
        self.audit.record(
            user_id=user.id,
            entity_type="Expense",
            entity_id=expense.id,
            action="CREATE",
            after_state={"amount": str(expense.amount), "expense_category": expense.expense_category},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        return expense

    def get(self, user: User, expense_id: uuid.UUID) -> Expense:
        expense = self.repo.get_owned(user.id, expense_id)
        if expense is None:
            raise NotFoundError("Expense not found.")
        return expense

    def list(
        self,
        user: User,
        *,
        financial_period_id: uuid.UUID | None,
        distribution_category_id: uuid.UUID | None,
        expense_category: str | None,
        payment_method: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Expense], int]:
        return self.repo.list(
            user.id,
            financial_period_id=financial_period_id,
            distribution_category_id=distribution_category_id,
            expense_category=expense_category,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    def delete(self, user: User, expense_id: uuid.UUID) -> None:
        expense = self.get(user, expense_id)
        self._ensure_period_open(user, expense.financial_period_id)
        before = {"amount": str(expense.amount)}
        self.repo.soft_delete(expense)
        self.audit.record(
            user_id=user.id,
            entity_type="Expense",
            entity_id=expense.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=expense.financial_period_id,
        )
        self.db.commit()
