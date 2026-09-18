import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.allowances.schemas import AllowanceCreate, AllowanceRead
from app.allowances.service import AllowanceService
from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.users.models import User

router = APIRouter(prefix="/allowances", tags=["allowances"])


@router.get("", response_model=Page[AllowanceRead])
def list_allowances(
    financial_period_id: uuid.UUID | None = None,
    name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[AllowanceRead]:
    rows, total = AllowanceService(db).list(
        current_user, financial_period_id=financial_period_id, name=name, page=page, page_size=page_size
    )
    return Page[AllowanceRead](
        data=[AllowanceRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("", response_model=AllowanceRead, status_code=status.HTTP_201_CREATED)
def create_allowance(
    payload: AllowanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllowanceRead:
    allowance = AllowanceService(db).create(current_user, payload)
    return AllowanceRead.model_validate(allowance)


@router.get("/{allowance_id}", response_model=AllowanceRead)
def get_allowance(
    allowance_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllowanceRead:
    allowance = AllowanceService(db).get(current_user, allowance_id)
    return AllowanceRead.model_validate(allowance)


@router.delete("/{allowance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allowance(
    allowance_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    AllowanceService(db).delete(current_user, allowance_id)
