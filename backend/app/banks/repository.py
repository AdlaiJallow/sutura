import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.banks.models import BankAccount
from app.common.repository_utils import count_query


class BankAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, account: BankAccount) -> BankAccount:
        self.db.add(account)
        self.db.flush()
        return account

    def get_owned(self, user_id: uuid.UUID, account_id: uuid.UUID) -> BankAccount | None:
        stmt = select(BankAccount).where(
            BankAccount.id == account_id, BankAccount.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self, user_id: uuid.UUID, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[BankAccount], int]:
        stmt = select(BankAccount).where(BankAccount.user_id == user_id)
        if is_active is not None:
            stmt = stmt.where(BankAccount.is_active == is_active)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(BankAccount.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def save(self, account: BankAccount) -> BankAccount:
        self.db.add(account)
        self.db.flush()
        return account
