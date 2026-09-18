from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.audit.repository import AuditRepository
from app.audit.schemas import AuditLogRead
from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.users.models import User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[AuditLogRead]:
    """Self-only audit trail (spec §36) — a user may only ever see their own audit history."""
    rows, total = AuditRepository(db).list_for_user(current_user.id, page=page, page_size=page_size)
    return Page[AuditLogRead](
        data=[AuditLogRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )
