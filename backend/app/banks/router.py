import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.banks.schemas import BankAccountCreate, BankAccountRead
from app.banks.service import BankAccountService
from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.users.models import User

router = APIRouter(prefix="/bank-accounts", tags=["banks"])


@router.get("", response_model=Page[BankAccountRead])
def list_bank_accounts(
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[BankAccountRead]:
    rows, total = BankAccountService(db).list(
        current_user, is_active=is_active, page=page, page_size=page_size
    )
    return Page[BankAccountRead](
        data=[BankAccountRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("", response_model=BankAccountRead, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    payload: BankAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankAccountRead:
    account = BankAccountService(db).create(current_user, payload)
    return BankAccountRead.model_validate(account)


@router.get("/{account_id}", response_model=BankAccountRead)
def get_bank_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankAccountRead:
    account = BankAccountService(db).get(current_user, account_id)
    return BankAccountRead.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_bank_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    BankAccountService(db).deactivate(current_user, account_id)
