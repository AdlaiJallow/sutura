import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.transactions.schemas import (
    BankTransactionCreate,
    BankTransactionRead,
    BankTransferCreate,
    BankTransferRead,
)
from app.transactions.service import BankTransactionService
from app.users.models import User

router = APIRouter(prefix="/bank-transactions", tags=["transactions"])


@router.get("", response_model=Page[BankTransactionRead])
def list_bank_transactions(
    bank_account_id: uuid.UUID | None = None,
    financial_period_id: uuid.UUID | None = None,
    transaction_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[BankTransactionRead]:
    rows, total = BankTransactionService(db).list(
        current_user,
        bank_account_id=bank_account_id,
        financial_period_id=financial_period_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page[BankTransactionRead](
        data=[BankTransactionRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("", response_model=BankTransactionRead, status_code=status.HTTP_201_CREATED)
def create_bank_transaction(
    payload: BankTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankTransactionRead:
    txn = BankTransactionService(db).create(current_user, payload)
    return BankTransactionRead.model_validate(txn)


@router.post("/transfer", response_model=BankTransferRead, status_code=status.HTTP_201_CREATED)
def create_bank_transfer(
    payload: BankTransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankTransferRead:
    out_txn, in_txn = BankTransactionService(db).transfer(current_user, payload)
    return BankTransferRead(
        transfer_pair_id=out_txn.transfer_pair_id,
        source_transaction=BankTransactionRead.model_validate(out_txn),
        destination_transaction=BankTransactionRead.model_validate(in_txn),
    )


@router.get("/{txn_id}", response_model=BankTransactionRead)
def get_bank_transaction(
    txn_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankTransactionRead:
    txn = BankTransactionService(db).get(current_user, txn_id)
    return BankTransactionRead.model_validate(txn)
