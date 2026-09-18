import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.allowances.models import Allowance
from app.common.repository_utils import count_query


class AllowanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, allowance: Allowance) -> Allowance:
        self.db.add(allowance)
        self.db.flush()
        return allowance

    def get_owned(self, user_id: uuid.UUID, allowance_id: uuid.UUID) -> Allowance | None:
        stmt = select(Allowance).where(
            Allowance.id == allowance_id,
            Allowance.user_id == user_id,
            Allowance.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        user_id: uuid.UUID,
        *,
        financial_period_id: uuid.UUID | None,
        name: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Allowance], int]:
        stmt = select(Allowance).where(Allowance.user_id == user_id, Allowance.deleted_at.is_(None))
        if financial_period_id is not None:
            stmt = stmt.where(Allowance.financial_period_id == financial_period_id)
        if name is not None:
            stmt = stmt.where(Allowance.name == name)
        total = count_query(self.db, stmt)
        stmt = stmt.order_by(Allowance.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def soft_delete(self, allowance: Allowance) -> None:
        allowance.deleted_at = datetime.now(timezone.utc)
        self.db.add(allowance)
        self.db.flush()
