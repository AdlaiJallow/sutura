import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.savings.schemas import SavingsItemCreate, SavingsItemRead, SavingsRead
from app.savings.service import SavingsItemService, SavingsService
from app.users.models import User

router = APIRouter(tags=["savings"])


@router.get("/savings/{period_id}", response_model=SavingsRead)
def get_savings_for_period(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsRead:
    row = SavingsService(db).get_for_period(current_user, period_id)
    return SavingsRead.model_validate(row)


@router.get("/savings-items", response_model=Page[SavingsItemRead])
def list_savings_items(
    financial_period_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SavingsItemRead]:
    rows, total = SavingsItemService(db).list(
        current_user, financial_period_id, page=page, page_size=page_size
    )
    return Page[SavingsItemRead](
        data=[SavingsItemRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("/savings-items", response_model=SavingsItemRead, status_code=status.HTTP_201_CREATED)
def create_savings_item(
    payload: SavingsItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsItemRead:
    item = SavingsItemService(db).create(current_user, payload)
    return SavingsItemRead.model_validate(item)


@router.get("/savings-items/{item_id}", response_model=SavingsItemRead)
def get_savings_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsItemRead:
    item = SavingsItemService(db).get(current_user, item_id)
    return SavingsItemRead.model_validate(item)


@router.delete("/savings-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    SavingsItemService(db).delete(current_user, item_id)
