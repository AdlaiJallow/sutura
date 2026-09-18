"""Reports module (spec §42) — placeholder for Phase 2. `monthly-summary` is real (it reuses
financial_periods' authoritative summary); every other report/export is a Phase 6 concern
(sync generation for small reports, Celery for exports) and returns 501 until then rather than
faking data.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.errors import AppError
from app.financial_periods.schemas import MonthlySummaryRead
from app.financial_periods.service import FinancialPeriodService
from app.users.models import User

router = APIRouter(prefix="/reports", tags=["reports"])


def _not_implemented(report_name: str) -> None:
    raise AppError(
        f"The '{report_name}' report is not implemented yet (planned for Phase 6).",
        code="NOT_IMPLEMENTED",
        status_code=501,
    )


@router.get("/monthly-summary/{period_id}", response_model=MonthlySummaryRead)
def monthly_summary_report(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlySummaryRead:
    summary = FinancialPeriodService(db).get_summary(current_user, period_id)
    return MonthlySummaryRead.model_validate(summary)


@router.get("/income")
def income_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("income")


@router.get("/expenses")
def expenses_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("expenses")


@router.get("/distribution")
def distribution_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("distribution")


@router.get("/savings")
def savings_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("savings")


@router.get("/bank-accounts")
def bank_accounts_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("bank-accounts")


@router.get("/planned-vs-actual")
def planned_vs_actual_report(financial_period_id: uuid.UUID, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("planned-vs-actual")


@router.get("/historical-comparison")
def historical_comparison_report(period_ids: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("historical-comparison")


@router.post("/{report_type}/export", status_code=202)
def export_report(report_type: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented(f"{report_type} export")


@router.get("/exports/{job_id}")
def export_status(job_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("export status polling")
