import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import NotFoundError
from app.distribution.models import DistributionCategory, DistributionRule
from app.distribution.repository import DistributionRepository
from app.distribution.schemas import DistributionRuleCreate
from app.users.models import User


class DistributionService:
    """Full CRUD is Phase 3 scope; this is the minimal, correctly-scoped slice needed so other
    modules (financial_periods) have something real to reference. 100% validation (D-009)
    happens in the schema layer today; a future phase adds the row-locked transactional
    re-validation for PATCH/replace-categories flows.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DistributionRepository(db)
        self.audit = AuditService(db)

    def create_rule(self, user: User, payload: DistributionRuleCreate) -> DistributionRule:
        rule = DistributionRule(user_id=user.id, name=payload.name, description=payload.description)
        self.repo.create_rule(rule)
        for cat in payload.categories:
            self.repo.add_category(
                DistributionCategory(
                    distribution_rule_id=rule.id,
                    name=cat.name,
                    percentage=cat.percentage,
                    contributes_to_automatic_savings=cat.contributes_to_automatic_savings,
                    is_unallocated_bucket=cat.is_unallocated_bucket,
                    display_order=cat.display_order,
                )
            )
        self.audit.record(
            user_id=user.id,
            entity_type="DistributionRule",
            entity_id=rule.id,
            action="CREATE",
            after_state={"name": rule.name, "categories": len(payload.categories)},
        )
        self.db.commit()
        return self.get_rule(user, rule.id)

    def get_rule(self, user: User, rule_id: uuid.UUID) -> DistributionRule:
        rule = self.repo.get_rule(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Distribution rule not found.")
        return rule

    def list_rules(
        self, user: User, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[DistributionRule], int]:
        return self.repo.list_rules(user.id, is_active=is_active, page=page, page_size=page_size)
