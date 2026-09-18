import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError
from app.financial_periods.repository import FinancialPeriodRepository
from app.salary.models import Salary
from app.salary.repository import SalaryRepository
from app.salary.schemas import SalaryCreate
from app.users.models import User


class SalaryService:
    """First non-financial_periods module wired end-to-end as a reference stub: real ownership
    scoping + closed-period guard + audit, but without the full validation matrix Phase 3 adds."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SalaryRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: SalaryCreate) -> Salary:
        self._ensure_period_open(user, payload.financial_period_id)
        if self.repo.get_for_period(user.id, payload.financial_period_id):
            raise ConflictError("A salary record already exists for this period.")
        salary = Salary(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            net_amount=payload.net_amount,
            currency=payload.currency.upper(),
            status=payload.status,
            notes=payload.notes,
        )
        self.repo.create(salary)
        self.audit.record(
            user_id=user.id,
            entity_type="Salary",
            entity_id=salary.id,
            action="CREATE",
            after_state={"net_amount": str(salary.net_amount)},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        return salary

    def get(self, user: User, salary_id: uuid.UUID) -> Salary:
        salary = self.repo.get_owned(user.id, salary_id)
        if salary is None:
            raise NotFoundError("Salary record not found.")
        return salary

    def list(
        self, user: User, financial_period_id: uuid.UUID | None, *, page: int, page_size: int
    ) -> tuple[list[Salary], int]:
        return self.repo.list_for_period(user.id, financial_period_id, page=page, page_size=page_size)

    def delete(self, user: User, salary_id: uuid.UUID) -> None:
        salary = self.get(user, salary_id)
        self._ensure_period_open(user, salary.financial_period_id)
        before = {"net_amount": str(salary.net_amount)}
        self.repo.soft_delete(salary)
        self.audit.record(
            user_id=user.id,
            entity_type="Salary",
            entity_id=salary.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=salary.financial_period_id,
        )
        self.db.commit()
