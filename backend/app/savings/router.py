import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.savings.schemas import (
    SavingsAllocationApplyRule,
    SavingsAllocationCreate,
    SavingsAllocationRead,
    SavingsDistributionRuleCreate,
    SavingsDistributionRuleItemsReplace,
    SavingsDistributionRuleRead,
    SavingsDistributionRuleUpdate,
    SavingsItemCreate,
    SavingsItemRead,
    SavingsItemUpdate,
    SavingsRead,
)
from app.savings.service import (
    SavingsAllocationService,
    SavingsDistributionRuleService,
    SavingsItemService,
    SavingsService,
)
from app.users.models import User

router = APIRouter(tags=["savings"])


@router.get("/savings/{period_id}", response_model=SavingsRead)
def get_savings_for_period(
    period_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsRead:
    row = SavingsService(db).get_for_period(current_user, period_id)
    return SavingsRead.model_validate(row)


@router.get("/savings-items", response_model=Page[SavingsItemRead])
def list_savings_items(
    financial_period_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SavingsItemRead]:
    rows, total = SavingsItemService(db).list(
        current_user, financial_period_id, page=page, page_size=page_size
    )
    return Page[SavingsItemRead](
        data=[SavingsItemRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post("/savings-items", response_model=SavingsItemRead, status_code=status.HTTP_201_CREATED)
def create_savings_item(
    payload: SavingsItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsItemRead:
    item = SavingsItemService(db).create(current_user, payload)
    return SavingsItemRead.model_validate(item)


@router.get("/savings-items/{item_id}", response_model=SavingsItemRead)
def get_savings_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsItemRead:
    item = SavingsItemService(db).get(current_user, item_id)
    return SavingsItemRead.model_validate(item)


@router.patch("/savings-items/{item_id}", response_model=SavingsItemRead)
def update_savings_item(
    item_id: uuid.UUID,
    payload: SavingsItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsItemRead:
    item = SavingsItemService(db).update(current_user, item_id, payload)
    return SavingsItemRead.model_validate(item)


@router.delete("/savings-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    SavingsItemService(db).delete(current_user, item_id)


# ---------------------------------------------------------------------------------------------
# SavingsDistributionRule (D-013)


@router.get(
    "/savings-distribution-rules", response_model=Page[SavingsDistributionRuleRead]
)
def list_savings_distribution_rules(
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SavingsDistributionRuleRead]:
    rows, total = SavingsDistributionRuleService(db).list_rules(
        current_user, is_active=is_active, page=page, page_size=page_size
    )
    return Page[SavingsDistributionRuleRead](
        data=[SavingsDistributionRuleRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post(
    "/savings-distribution-rules",
    response_model=SavingsDistributionRuleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_savings_distribution_rule(
    payload: SavingsDistributionRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsDistributionRuleRead:
    rule = SavingsDistributionRuleService(db).create_rule(current_user, payload)
    return SavingsDistributionRuleRead.model_validate(rule)


@router.get(
    "/savings-distribution-rules/{rule_id}", response_model=SavingsDistributionRuleRead
)
def get_savings_distribution_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsDistributionRuleRead:
    rule = SavingsDistributionRuleService(db).get_rule(current_user, rule_id)
    return SavingsDistributionRuleRead.model_validate(rule)


@router.patch(
    "/savings-distribution-rules/{rule_id}", response_model=SavingsDistributionRuleRead
)
def update_savings_distribution_rule(
    rule_id: uuid.UUID,
    payload: SavingsDistributionRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsDistributionRuleRead:
    rule = SavingsDistributionRuleService(db).update_rule(current_user, rule_id, payload)
    return SavingsDistributionRuleRead.model_validate(rule)


@router.put(
    "/savings-distribution-rules/{rule_id}/items", response_model=SavingsDistributionRuleRead
)
def replace_savings_distribution_rule_items(
    rule_id: uuid.UUID,
    payload: SavingsDistributionRuleItemsReplace,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsDistributionRuleRead:
    rule = SavingsDistributionRuleService(db).replace_items(current_user, rule_id, payload)
    return SavingsDistributionRuleRead.model_validate(rule)


# ---------------------------------------------------------------------------------------------
# SavingsAllocation (D-014, §19/§20)


@router.get("/savings-allocations", response_model=Page[SavingsAllocationRead])
def list_savings_allocations(
    financial_period_id: uuid.UUID,
    allocation_method: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SavingsAllocationRead]:
    rows, total = SavingsAllocationService(db).list(
        current_user,
        financial_period_id,
        allocation_method=allocation_method,
        page=page,
        page_size=page_size,
    )
    return Page[SavingsAllocationRead](
        data=[SavingsAllocationRead.model_validate(r) for r in rows],
        meta=paginate_meta(page, page_size, total),
    )


@router.post(
    "/savings-allocations", response_model=SavingsAllocationRead, status_code=status.HTTP_201_CREATED
)
def create_savings_allocation(
    payload: SavingsAllocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsAllocationRead:
    allocation = SavingsAllocationService(db).create(current_user, payload)
    return SavingsAllocationRead.model_validate(allocation)


@router.post(
    "/savings-allocations/apply-rule", response_model=list[SavingsAllocationRead]
)
def apply_savings_distribution_rule(
    payload: SavingsAllocationApplyRule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavingsAllocationRead]:
    allocations = SavingsAllocationService(db).apply_rule(
        current_user, payload.financial_period_id, payload.savings_distribution_rule_id
    )
    return [SavingsAllocationRead.model_validate(a) for a in allocations]


@router.get("/savings-allocations/{allocation_id}", response_model=SavingsAllocationRead)
def get_savings_allocation(
    allocation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavingsAllocationRead:
    allocation = SavingsAllocationService(db).get(current_user, allocation_id)
    return SavingsAllocationRead.model_validate(allocation)


@router.delete("/savings-allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_allocation(
    allocation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    SavingsAllocationService(db).delete(current_user, allocation_id)
