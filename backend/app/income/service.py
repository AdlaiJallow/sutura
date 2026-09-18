import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.financial_periods.repository import FinancialPeriodRepository
from app.income.models import Income
from app.income.repository import IncomeRepository
from app.income.schemas import IncomeCreate, IncomeUpdate
from app.users.models import User


class IncomeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = IncomeRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: IncomeCreate) -> Income:
        self._ensure_period_open(user, payload.financial_period_id)
        income = Income(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            income_type=payload.income_type,
            description=payload.description,
            amount=payload.amount,
            currency=payload.currency.upper(),
            date_received=payload.date_received,
            source=payload.source,
            is_recurring=payload.is_recurring,
            notes=payload.notes,
        )
        self.repo.create(income)
        self.audit.record(
            user_id=user.id,
            entity_type="Income",
            entity_id=income.id,
            action="CREATE",
            after_state={"amount": str(income.amount), "income_type": income.income_type},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        return income

    def update(self, user: User, income_id: uuid.UUID, payload: IncomeUpdate) -> Income:
        income = self.get(user, income_id)
        self._ensure_period_open(user, income.financial_period_id)

        values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        if not values:
            raise ValidationAppError("No fields provided to update.")
        if values.get("currency"):
            values["currency"] = values["currency"].upper()

        before = {
            "income_type": income.income_type,
            "description": income.description,
            "amount": str(income.amount),
            "currency": income.currency,
            "source": income.source,
            "notes": income.notes,
        }

        rowcount = self.repo.update_owned(user.id, income_id, payload.expected_updated_at, values)
        if rowcount == 0:
            raise ConflictError(
                "This income record was modified by another request. Reload and try again."
            )

        updated = self.get(user, income_id)
        self.audit.record(
            user_id=user.id,
            entity_type="Income",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "income_type": updated.income_type,
                "description": updated.description,
                "amount": str(updated.amount),
                "currency": updated.currency,
                "source": updated.source,
                "notes": updated.notes,
            },
            related_record_type="FinancialPeriod",
            related_record_id=updated.financial_period_id,
        )
        self.db.commit()
        return updated

    def get(self, user: User, income_id: uuid.UUID) -> Income:
        income = self.repo.get_owned(user.id, income_id)
        if income is None:
            raise NotFoundError("Income record not found.")
        return income

    def list(
        self,
        user: User,
        *,
        financial_period_id: uuid.UUID | None,
        income_type: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Income], int]:
        return self.repo.list(
            user.id,
            financial_period_id=financial_period_id,
            income_type=income_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    def delete(self, user: User, income_id: uuid.UUID) -> None:
        income = self.get(user, income_id)
        self._ensure_period_open(user, income.financial_period_id)
        before = {"amount": str(income.amount)}
        self.repo.soft_delete(income)
        self.audit.record(
            user_id=user.id,
            entity_type="Income",
            entity_id=income.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=income.financial_period_id,
        )
        self.db.commit()
