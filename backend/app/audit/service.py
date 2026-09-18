import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.audit.repository import AuditRepository


class AuditService:
    """Write helper used by every module that mutates a financial record (write-only
    dependency — audit never reads back into other modules' business logic)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AuditRepository(db)

    def record(
        self,
        *,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        related_record_type: str | None = None,
        related_record_id: uuid.UUID | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_state=before_state,
            after_state=after_state,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
        )
        return self.repo.add(entry)
