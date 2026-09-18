"""Analytics module (spec §24) — placeholder. Cross-period trend/aggregate endpoints are built
in Phase 6 on top of a stable financial core; all return 501 for now rather than fabricating
numbers (never accept/emit a client-supplied aggregate, §46)."""
from fastapi import APIRouter, Depends

from app.common.deps import get_current_user
from app.common.errors import AppError
from app.users.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _not_implemented(name: str) -> None:
    raise AppError(
        f"The '{name}' analytics endpoint is not implemented yet (planned for Phase 6).",
        code="NOT_IMPLEMENTED",
        status_code=501,
    )


@router.get("/income-trend")
def income_trend(months: int = 12, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("income-trend")


@router.get("/expense-trend")
def expense_trend(months: int = 12, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("expense-trend")


@router.get("/savings-trend")
def savings_trend(months: int = 12, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("savings-trend")


@router.get("/savings-rate")
def savings_rate(months: int = 12, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("savings-rate")


@router.get("/spending-by-category")
def spending_by_category(financial_period_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("spending-by-category")


@router.get("/income-by-source")
def income_by_source(financial_period_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("income-by-source")


@router.get("/planned-vs-actual")
def planned_vs_actual(financial_period_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("planned-vs-actual")


@router.get("/bank-growth")
def bank_growth(months: int = 12, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("bank-growth")


@router.get("/unused-allocations")
def unused_allocations(financial_period_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("unused-allocations")


@router.get("/overspending")
def overspending(financial_period_id: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("overspending")


@router.get("/month-comparison")
def month_comparison(period_ids: str, current_user: User = Depends(get_current_user)) -> None:
    _not_implemented("month-comparison")
