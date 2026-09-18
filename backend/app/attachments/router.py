import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.attachments.schemas import AttachmentRead
from app.attachments.service import AttachmentService
from app.common.database import get_db
from app.common.deps import get_current_user
from app.users.models import User

router = APIRouter(prefix="/expenses", tags=["attachments"])


@router.post(
    "/{expense_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    expense_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttachmentRead:
    contents = await file.read()
    attachment = AttachmentService(db).upload(
        current_user,
        expense_id,
        file_name=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(contents),
    )
    return AttachmentRead.model_validate(attachment)


@router.get("/{expense_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttachmentRead]:
    rows = AttachmentService(db).list_for_expense(current_user, expense_id)
    return [AttachmentRead.model_validate(r) for r in rows]


@router.delete("/{expense_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    expense_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    AttachmentService(db).delete(current_user, expense_id, attachment_id)
