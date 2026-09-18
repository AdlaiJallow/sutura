import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.distribution.models import DistributionCategory
from app.expenses.models import Expense
from app.expenses.repository import ExpenseRepository
from app.expenses.schemas import ExpenseCreate, ExpenseUpdate
from app.financial_periods.models import FinancialPeriod
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

    def _validate_distribution_category(
        self, period: FinancialPeriod, distribution_category_id: uuid.UUID | None
    ) -> None:
        """D-006 ERD note on `Expense.distribution_category_id`: nullable only transiently,
        before a period has a distribution rule selected; required, and must belong to that
        exact rule, once one is selected. Enforced here in the service layer — never trusted
        from the FK alone, since the FK doesn't know which rule is "the period's rule"."""
        if period.distribution_rule_id is None:
            return
        if distribution_category_id is None:
            raise ValidationAppError(
                "distribution_category_id is required once a distribution rule has been "
                "selected for this financial period."
            )
        category = self.db.execute(
            select(DistributionCategory).where(
                DistributionCategory.id == distribution_category_id,
                DistributionCategory.distribution_rule_id == period.distribution_rule_id,
            )
        ).scalar_one_or_none()
        if category is None:
            raise ValidationAppError(
                "distribution_category_id does not belong to this period's selected "
                "distribution rule."
            )

    def create(self, user: User, payload: ExpenseCreate) -> Expense:
        period = self._ensure_period_open(user, payload.financial_period_id)
        self._validate_distribution_category(period, payload.distribution_category_id)
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

    def update(self, user: User, expense_id: uuid.UUID, payload: ExpenseUpdate) -> Expense:
        expense = self.get(user, expense_id)
        period = self._ensure_period_open(user, expense.financial_period_id)

        values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        if not values:
            raise ValidationAppError("No fields provided to update.")
        if values.get("currency"):
            values["currency"] = values["currency"].upper()

        effective_category_id = values.get(
            "distribution_category_id", expense.distribution_category_id
        )
        self._validate_distribution_category(period, effective_category_id)

        before = {
            "name": expense.name,
            "expense_category": expense.expense_category,
            "amount": str(expense.amount),
            "currency": expense.currency,
            "distribution_category_id": str(expense.distribution_category_id)
            if expense.distribution_category_id
            else None,
            "payment_method": expense.payment_method,
            "notes": expense.notes,
        }

        rowcount = self.repo.update_owned(user.id, expense_id, payload.expected_updated_at, values)
        if rowcount == 0:
            raise ConflictError(
                "This expense was modified by another request. Reload and try again."
            )

        updated = self.get(user, expense_id)
        self.audit.record(
            user_id=user.id,
            entity_type="Expense",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": updated.name,
                "expense_category": updated.expense_category,
                "amount": str(updated.amount),
                "currency": updated.currency,
                "distribution_category_id": str(updated.distribution_category_id)
                if updated.distribution_category_id
                else None,
                "payment_method": updated.payment_method,
                "notes": updated.notes,
            },
            related_record_type="FinancialPeriod",
            related_record_id=updated.financial_period_id,
        )
        self.db.commit()
        return updated

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
