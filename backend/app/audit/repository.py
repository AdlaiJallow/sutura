import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entry: AuditLog) -> AuditLog:
        self.db.add(entry)
        self.db.flush()
        return entry

    def list_for_user(
        self, user_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.user_id == user_id)
        total = self.db.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()
        stmt = (
            base.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total
