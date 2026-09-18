import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.expenses.schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate
from app.expenses.service import ExpenseService
from app.users.models import User

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=Page[ExpenseRead])
def list_expenses(
    financial_period_id: uuid.UUID | None = None,
    distribution_category_id: uuid.UUID | None = None,
    expense_category: str | None = None,
    payment_method: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ExpenseRead]:
    rows, total = ExpenseService(db).list(
        current_user,
        financial_period_id=financial_period_id,
        distribution_category_id=distribution_category_id,
        expense_category=expense_category,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page[ExpenseRead](
        data=[ExpenseRead.model_validate(r) for r in rows], meta=paginate_meta(page, page_size, total)
    )


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseRead:
    expense = ExpenseService(db).create(current_user, payload)
    return ExpenseRead.model_validate(expense)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseRead:
    expense = ExpenseService(db).get(current_user, expense_id)
    return ExpenseRead.model_validate(expense)


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseRead:
    expense = ExpenseService(db).update(current_user, expense_id, payload)
    return ExpenseRead.model_validate(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    ExpenseService(db).delete(current_user, expense_id)
