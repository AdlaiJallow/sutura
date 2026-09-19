"""GET /distributions/{period_id} — read-only computed distribution view (docs/api-contract.md
§9). A separate router/prefix from `distribution_router` (`/distribution-rules`): these are
different resource shapes despite the similar name — CRUD rule definitions (name + percentage)
vs. a period's server-computed allocation/used/remaining amounts. No business logic here; the
route only calls `FinancialPeriodService.get_distribution_view` and maps the result to a schema.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.distribution.schemas import DistributionViewRead
from app.financial_periods.service import FinancialPeriodService
from app.users.models import User

router = APIRouter(prefix="/distributions", tags=["distributions"])


@router.get("/{period_id}", response_model=DistributionViewRead)
def get_distribution_view(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionViewRead:
    view = FinancialPeriodService(db).get_distribution_view(current_user, period_id)
    return DistributionViewRead.model_validate(view)
