import uuid

from sqlalchemy.orm import Session

from app.allowances.models import Allowance
from app.allowances.repository import AllowanceRepository
from app.allowances.schemas import AllowanceCreate, AllowanceUpdate
from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.financial_periods.repository import FinancialPeriodRepository
from app.users.models import User


class AllowanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AllowanceRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: AllowanceCreate) -> Allowance:
        self._ensure_period_open(user, payload.financial_period_id)
        allowance = Allowance(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            name=payload.name,
            amount=payload.amount,
            currency=payload.currency.upper(),
            is_recurring=payload.is_recurring,
            date_received=payload.date_received,
            notes=payload.notes,
        )
        self.repo.create(allowance)
        self.audit.record(
            user_id=user.id,
            entity_type="Allowance",
            entity_id=allowance.id,
            action="CREATE",
            after_state={"name": allowance.name, "amount": str(allowance.amount)},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        return allowance

    def update(self, user: User, allowance_id: uuid.UUID, payload: AllowanceUpdate) -> Allowance:
        allowance = self.get(user, allowance_id)
        self._ensure_period_open(user, allowance.financial_period_id)

        values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        if not values:
            raise ValidationAppError("No fields provided to update.")
        if values.get("currency"):
            values["currency"] = values["currency"].upper()

        before = {
            "name": allowance.name,
            "amount": str(allowance.amount),
            "currency": allowance.currency,
            "is_recurring": allowance.is_recurring,
            "date_received": str(allowance.date_received),
            "notes": allowance.notes,
        }

        rowcount = self.repo.update_owned(
            user.id, allowance_id, payload.expected_updated_at, values
        )
        if rowcount == 0:
            raise ConflictError(
                "This allowance was modified by another request. Reload and try again."
            )

        updated = self.get(user, allowance_id)
        self.audit.record(
            user_id=user.id,
            entity_type="Allowance",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": updated.name,
                "amount": str(updated.amount),
                "currency": updated.currency,
                "is_recurring": updated.is_recurring,
                "date_received": str(updated.date_received),
                "notes": updated.notes,
            },
            related_record_type="FinancialPeriod",
            related_record_id=updated.financial_period_id,
        )
        self.db.commit()
        return updated

    def get(self, user: User, allowance_id: uuid.UUID) -> Allowance:
        allowance = self.repo.get_owned(user.id, allowance_id)
        if allowance is None:
            raise NotFoundError("Allowance not found.")
        return allowance

    def list(
        self,
        user: User,
        *,
        financial_period_id: uuid.UUID | None,
        name: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Allowance], int]:
        return self.repo.list(
            user.id, financial_period_id=financial_period_id, name=name, page=page, page_size=page_size
        )

    def delete(self, user: User, allowance_id: uuid.UUID) -> None:
        allowance = self.get(user, allowance_id)
        self._ensure_period_open(user, allowance.financial_period_id)
        before = {"amount": str(allowance.amount)}
        self.repo.soft_delete(allowance)
        self.audit.record(
            user_id=user.id,
            entity_type="Allowance",
            entity_id=allowance.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=allowance.financial_period_id,
        )
        self.db.commit()
