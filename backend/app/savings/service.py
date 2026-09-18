import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.financial_periods.repository import FinancialPeriodRepository
from app.savings.models import Savings, SavingsItem
from app.savings.repository import SavingsItemRepository, SavingsRepository
from app.savings.schemas import SavingsItemCreate, SavingsItemUpdate
from app.users.models import User


class SavingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsRepository(db)
        self.periods = FinancialPeriodRepository(db)

    def get_for_period(self, user: User, period_id: uuid.UUID) -> Savings:
        period = self.periods.get_owned(user.id, period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        row = self.repo.get_for_period(user.id, period_id)
        if row is not None:
            return row
        # No calculation has run yet (e.g. a brand-new period) — synthesize a zeroed view
        # rather than 404, since the period itself is real. financial_periods.get_summary
        # performs the authoritative recalculation.
        return Savings(
            id=uuid.uuid4(),
            user_id=user.id,
            financial_period_id=period_id,
            automatic_savings_computed=Decimal("0"),
            manual_savings_total=Decimal("0"),
            final_savings_total=Decimal("0"),
            distributed_total=Decimal("0"),
            undistributed_total=Decimal("0"),
            last_calculated_at=None,
        )


class SavingsItemService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsItemRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.savings = SavingsRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: SavingsItemCreate) -> SavingsItem:
        self._ensure_period_open(user, payload.financial_period_id)
        savings_row = self.savings.get_for_period(user.id, payload.financial_period_id)
        if savings_row is None:
            savings_row = Savings(
                user_id=user.id,
                financial_period_id=payload.financial_period_id,
                last_calculated_at=datetime.now(timezone.utc),
            )
            self.db.add(savings_row)
            self.db.flush()

        item = SavingsItem(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            savings_id=savings_row.id,
            name=payload.name,
            amount=payload.amount,
            currency=payload.currency.upper(),
            date=payload.date,
            destination=payload.destination,
            notes=payload.notes,
        )
        self.repo.create(item)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=item.id,
            action="CREATE",
            after_state={"amount": str(item.amount)},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        # NOTE: recalculating the Savings cache (automatic/final/undistributed) happens the
        # next time financial_periods.get_summary/close is called (D-012); a live trigger here
        # is Phase 3 wiring once the full distribution engine exists.
        return item

    def update(self, user: User, item_id: uuid.UUID, payload: SavingsItemUpdate) -> SavingsItem:
        item = self.get(user, item_id)
        self._ensure_period_open(user, item.financial_period_id)

        values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        if not values:
            raise ValidationAppError("No fields provided to update.")
        if values.get("currency"):
            values["currency"] = values["currency"].upper()

        before = {
            "name": item.name,
            "amount": str(item.amount),
            "currency": item.currency,
            "date": str(item.date),
            "destination": item.destination,
            "notes": item.notes,
        }

        rowcount = self.repo.update_owned(user.id, item_id, payload.expected_updated_at, values)
        if rowcount == 0:
            raise ConflictError(
                "This savings item was modified by another request. Reload and try again."
            )

        updated = self.get(user, item_id)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": updated.name,
                "amount": str(updated.amount),
                "currency": updated.currency,
                "date": str(updated.date),
                "destination": updated.destination,
                "notes": updated.notes,
            },
            related_record_type="FinancialPeriod",
            related_record_id=updated.financial_period_id,
        )
        self.db.commit()
        # NOTE: same as create() — the Savings cache recalculation happens the next time
        # financial_periods.get_summary/close runs (D-012), not synchronously here.
        return updated

    def get(self, user: User, item_id: uuid.UUID) -> SavingsItem:
        item = self.repo.get_owned(user.id, item_id)
        if item is None:
            raise NotFoundError("Savings item not found.")
        return item

    def list(
        self, user: User, financial_period_id: uuid.UUID | None, *, page: int, page_size: int
    ) -> tuple[list[SavingsItem], int]:
        return self.repo.list(user.id, financial_period_id=financial_period_id, page=page, page_size=page_size)

    def delete(self, user: User, item_id: uuid.UUID) -> None:
        item = self.get(user, item_id)
        self._ensure_period_open(user, item.financial_period_id)
        before = {"amount": str(item.amount)}
        self.repo.soft_delete(item)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=item.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=item.financial_period_id,
        )
        self.db.commit()
