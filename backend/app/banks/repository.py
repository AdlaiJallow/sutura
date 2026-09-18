import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
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

    def update_owned(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        expected_updated_at: datetime,
        values: dict[str, Any],
    ) -> int:
        """Same atomic optimistic-locking technique as `common.repository_utils.conditional_update`
        (D-018), but written by hand here instead of sharing that helper: `BankAccount` has no
        `deleted_at` column (it is deactivated via `is_active`, not soft-deleted — spec §17 has
        no notion of a deleted bank account, only an inactive one), and the shared helper's WHERE
        clause unconditionally filters on `model.deleted_at.is_(None)`, which would raise on a
        model lacking that column."""
        if not values:
            return 0
        stmt = (
            update(BankAccount)
            .where(
                BankAccount.id == account_id,
                BankAccount.user_id == user_id,
                BankAccount.updated_at == expected_updated_at,
            )
            .values(**values)
        )
        result = self.db.execute(stmt)
        return result.rowcount
