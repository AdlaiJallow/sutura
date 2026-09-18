import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.banks.repository import BankAccountRepository
from app.common.errors import NotFoundError, ValidationAppError
from app.financial_periods.repository import FinancialPeriodRepository
from app.transactions.models import BankTransaction
from app.transactions.repository import BankTransactionRepository
from app.transactions.schemas import BankTransactionCreate
from app.users.models import User

SIGN_BY_TYPE = {
    "DEPOSIT": 1,
    "TRANSFER_IN": 1,
    "WITHDRAWAL": -1,
    "TRANSFER_OUT": -1,
    "ADJUSTMENT": 1,
}


class BankTransactionService:
    """Append-only ledger (D-016): no PATCH/DELETE. `current_balance` on the account is
    recalculated transactionally on every insert (D-011)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BankTransactionRepository(db)
        self.accounts = BankAccountRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def create(self, user: User, payload: BankTransactionCreate) -> BankTransaction:
        if payload.transaction_type not in ("DEPOSIT", "WITHDRAWAL", "ADJUSTMENT"):
            raise ValidationAppError(
                "transaction_type must be DEPOSIT, WITHDRAWAL, or ADJUSTMENT "
                "(transfers use POST /bank-transactions/transfer)."
            )
        account = self.accounts.get_owned(user.id, payload.bank_account_id)
        if account is None:
            raise NotFoundError("Bank account not found.")
        period = self.periods.get_owned(user.id, payload.financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")

        txn = BankTransaction(
            user_id=user.id,
            bank_account_id=payload.bank_account_id,
            financial_period_id=payload.financial_period_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            currency=payload.currency.upper(),
            transaction_date=payload.transaction_date,
            description=payload.description,
            related_record_type="MANUAL",
        )
        self.repo.create(txn)

        sign = SIGN_BY_TYPE[payload.transaction_type]
        account.current_balance = Decimal(account.current_balance) + sign * Decimal(payload.amount)
        self.accounts.save(account)

        self.audit.record(
            user_id=user.id,
            entity_type="BankTransaction",
            entity_id=txn.id,
            action="CREATE",
            after_state={"amount": str(txn.amount), "transaction_type": txn.transaction_type},
            related_record_type="BankAccount",
            related_record_id=account.id,
        )
        self.db.commit()
        return txn

    def get(self, user: User, txn_id: uuid.UUID) -> BankTransaction:
        txn = self.repo.get_owned(user.id, txn_id)
        if txn is None:
            raise NotFoundError("Bank transaction not found.")
        return txn

    def list(
        self,
        user: User,
        *,
        bank_account_id: uuid.UUID | None,
        financial_period_id: uuid.UUID | None,
        transaction_type: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[BankTransaction], int]:
        return self.repo.list(
            user.id,
            bank_account_id=bank_account_id,
            financial_period_id=financial_period_id,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
