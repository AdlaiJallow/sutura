import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.financial_periods.schemas import (
    FinancialPeriodCreate,
    FinancialPeriodPatch,
    FinancialPeriodRead,
    MonthlySummaryRead,
    ReopenRequest,
    SelectDistributionRuleRequest,
)
from app.financial_periods.service import FinancialPeriodService
from app.users.models import User

router = APIRouter(prefix="/financial-periods", tags=["financial-periods"])


@router.get("", response_model=Page[FinancialPeriodRead])
def list_financial_periods(
    year: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[FinancialPeriodRead]:
    rows, total = FinancialPeriodService(db).list_periods(
        current_user, year=year, status=status_filter, page=page, page_size=page_size
    )
    return Page[FinancialPeriodRead](
        data=[FinancialPeriodRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("", response_model=FinancialPeriodRead, status_code=status.HTTP_201_CREATED)
def create_financial_period(
    payload: FinancialPeriodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).create_period(current_user, payload)
    return FinancialPeriodRead.model_validate(period)


@router.get("/current", response_model=FinancialPeriodRead)
def get_current_period(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).get_or_create_current(current_user)
    return FinancialPeriodRead.model_validate(period)


@router.get("/{period_id}", response_model=FinancialPeriodRead)
def get_financial_period(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).get_period(current_user, period_id)
    return FinancialPeriodRead.model_validate(period)


@router.patch("/{period_id}", response_model=FinancialPeriodRead)
def patch_financial_period(
    period_id: uuid.UUID,
    payload: FinancialPeriodPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).patch_period(current_user, period_id, payload.notes)
    return FinancialPeriodRead.model_validate(period)


@router.post("/{period_id}/close", response_model=FinancialPeriodRead)
def close_financial_period(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).close_period(current_user, period_id)
    return FinancialPeriodRead.model_validate(period)


@router.post("/{period_id}/reopen", response_model=FinancialPeriodRead)
def reopen_financial_period(
    period_id: uuid.UUID,
    payload: ReopenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).reopen_period(current_user, period_id, payload.reason)
    return FinancialPeriodRead.model_validate(period)


@router.post("/{period_id}/select-distribution-rule", response_model=FinancialPeriodRead)
def select_distribution_rule(
    period_id: uuid.UUID,
    payload: SelectDistributionRuleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialPeriodRead:
    period = FinancialPeriodService(db).select_distribution_rule(
        current_user, period_id, payload.distribution_rule_id
    )
    return FinancialPeriodRead.model_validate(period)


@router.get("/{period_id}/summary", response_model=MonthlySummaryRead)
def get_financial_period_summary(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlySummaryRead:
    summary = FinancialPeriodService(db).get_summary(current_user, period_id)
    return MonthlySummaryRead.model_validate(summary)
