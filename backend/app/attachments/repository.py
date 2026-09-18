import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attachments.models import Attachment


class AttachmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, attachment: Attachment) -> Attachment:
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def get_owned(self, user_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == user_id,
            Attachment.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_expense(self, user_id: uuid.UUID, expense_id: uuid.UUID) -> list[Attachment]:
        stmt = select(Attachment).where(
            Attachment.user_id == user_id,
            Attachment.expense_id == expense_id,
            Attachment.deleted_at.is_(None),
        )
        return list(self.db.execute(stmt).scalars().all())

    def soft_delete(self, attachment: Attachment) -> None:
        attachment.deleted_at = datetime.now(timezone.utc)
        self.db.add(attachment)
        self.db.flush()
