import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.income.schemas import IncomeCreate, IncomeRead
from app.income.service import IncomeService
from app.users.models import User

router = APIRouter(prefix="/income", tags=["income"])


@router.get("", response_model=Page[IncomeRead])
def list_income(
    financial_period_id: uuid.UUID | None = None,
    income_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[IncomeRead]:
    rows, total = IncomeService(db).list(
        current_user,
        financial_period_id=financial_period_id,
        income_type=income_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page[IncomeRead](
        data=[IncomeRead.model_validate(r) for r in rows], meta=paginate_meta(page, page_size, total)
    )


@router.post("", response_model=IncomeRead, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IncomeRead:
    income = IncomeService(db).create(current_user, payload)
    return IncomeRead.model_validate(income)


@router.get("/{income_id}", response_model=IncomeRead)
def get_income(
    income_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IncomeRead:
    income = IncomeService(db).get(current_user, income_id)
    return IncomeRead.model_validate(income)


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    income_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    IncomeService(db).delete(current_user, income_id)
