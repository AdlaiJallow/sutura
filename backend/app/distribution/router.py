import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.distribution.schemas import (
    DistributionCategoriesReplace,
    DistributionRuleCreate,
    DistributionRuleRead,
    DistributionRuleUpdate,
)
from app.distribution.service import DistributionService
from app.users.models import User

router = APIRouter(prefix="/distribution-rules", tags=["distribution"])


@router.get("", response_model=Page[DistributionRuleRead])
def list_distribution_rules(
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[DistributionRuleRead]:
    rows, total = DistributionService(db).list_rules(
        current_user, is_active=is_active, page=page, page_size=page_size
    )
    return Page[DistributionRuleRead](
        data=[DistributionRuleRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("", response_model=DistributionRuleRead, status_code=status.HTTP_201_CREATED)
def create_distribution_rule(
    payload: DistributionRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionRuleRead:
    rule = DistributionService(db).create_rule(current_user, payload)
    return DistributionRuleRead.model_validate(rule)


@router.get("/{rule_id}", response_model=DistributionRuleRead)
def get_distribution_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionRuleRead:
    rule = DistributionService(db).get_rule(current_user, rule_id)
    return DistributionRuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=DistributionRuleRead)
def update_distribution_rule(
    rule_id: uuid.UUID,
    payload: DistributionRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionRuleRead:
    rule = DistributionService(db).update_rule(current_user, rule_id, payload)
    return DistributionRuleRead.model_validate(rule)


@router.put("/{rule_id}/categories", response_model=DistributionRuleRead)
def replace_distribution_rule_categories(
    rule_id: uuid.UUID,
    payload: DistributionCategoriesReplace,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionRuleRead:
    rule = DistributionService(db).replace_categories(current_user, rule_id, payload)
    return DistributionRuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_distribution_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    DistributionService(db).deactivate_rule(current_user, rule_id)
