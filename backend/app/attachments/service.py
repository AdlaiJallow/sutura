import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.attachments.models import Attachment
from app.attachments.repository import AttachmentRepository
from app.audit.service import AuditService
from app.common.errors import NotFoundError, ValidationAppError
from app.expenses.repository import ExpenseRepository
from app.users.models import User

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class AttachmentService:
    """S3 upload plumbing (spec §16/attachments module) is a Phase 4 concern — the real
    boto3 PUT is not wired up yet. This validates type/size server-side (§34) and persists
    metadata with a deterministic storage_key so the upload call can be dropped in later
    without a schema change.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AttachmentRepository(db)
        self.expenses = ExpenseRepository(db)
        self.audit = AuditService(db)

    def upload(
        self,
        user: User,
        expense_id: uuid.UUID,
        *,
        file_name: str,
        content_type: str,
        file_size_bytes: int,
    ) -> Attachment:
        expense = self.expenses.get_owned(user.id, expense_id)
        if expense is None:
            raise NotFoundError("Expense not found.")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationAppError(f"Unsupported file type: {content_type}.")
        if file_size_bytes <= 0 or file_size_bytes > MAX_FILE_SIZE_BYTES:
            raise ValidationAppError("File size must be between 1 byte and 10MB.")

        storage_key = f"expenses/{expense_id}/{uuid.uuid4()}-{file_name}"
        attachment = Attachment(
            user_id=user.id,
            expense_id=expense_id,
            file_name=file_name,
            storage_key=storage_key,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            uploaded_at=datetime.now(timezone.utc),
        )
        self.repo.create(attachment)
        self.audit.record(
            user_id=user.id,
            entity_type="Attachment",
            entity_id=attachment.id,
            action="CREATE",
            after_state={"file_name": file_name},
            related_record_type="Expense",
            related_record_id=expense_id,
        )
        self.db.commit()
        return attachment

    def list_for_expense(self, user: User, expense_id: uuid.UUID) -> list[Attachment]:
        expense = self.expenses.get_owned(user.id, expense_id)
        if expense is None:
            raise NotFoundError("Expense not found.")
        return self.repo.list_for_expense(user.id, expense_id)

    def delete(self, user: User, expense_id: uuid.UUID, attachment_id: uuid.UUID) -> None:
        attachment = self.repo.get_owned(user.id, attachment_id)
        if attachment is None or attachment.expense_id != expense_id:
            raise NotFoundError("Attachment not found.")
        self.repo.soft_delete(attachment)
        self.audit.record(
            user_id=user.id,
            entity_type="Attachment",
            entity_id=attachment.id,
            action="DELETE",
            related_record_type="Expense",
            related_record_id=expense_id,
        )
        self.db.commit()
