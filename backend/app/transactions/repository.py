import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repository_utils import count_query
from app.transactions.models import BankTransaction


class BankTransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, txn: BankTransaction) -> BankTransaction:
        self.db.add(txn)
        self.db.flush()
        return txn

    def get_owned(self, user_id: uuid.UUID, txn_id: uuid.UUID) -> BankTransaction | None:
        stmt = select(BankTransaction).where(
            BankTransaction.id == txn_id, BankTransaction.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        user_id: uuid.UUID,
        *,
        bank_account_id: uuid.UUID | None,
        financial_period_id: uuid.UUID | None,
        transaction_type: str | None,
        date_from,
        date_to,
        page: int,
        page_size: int,
    ) -> tuple[list[BankTransaction], int]:
        stmt = select(BankTransaction).where(BankTransaction.user_id == user_id)
        if bank_account_id is not None:
            stmt = stmt.where(BankTransaction.bank_account_id == bank_account_id)
        if financial_period_id is not None:
            stmt = stmt.where(BankTransaction.financial_period_id == financial_period_id)
        if transaction_type is not None:
            stmt = stmt.where(BankTransaction.transaction_type == transaction_type)
        if date_from is not None:
            stmt = stmt.where(BankTransaction.transaction_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(BankTransaction.transaction_date <= date_to)
        total = count_query(self.db, stmt)
        stmt = (
            stmt.order_by(BankTransaction.transaction_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total
