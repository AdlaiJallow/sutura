import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.distribution.models import DistributionCategory, DistributionRule
from app.distribution.repository import DistributionRepository
from app.distribution.schemas import (
    DistributionCategoriesReplace,
    DistributionRuleCreate,
    DistributionRuleUpdate,
)
from app.users.models import User

HUNDRED = Decimal("100.00")


class DistributionService:
    """Full CRUD is Phase 3 scope. 100%-sum validation (D-009) happens at the schema layer for
    the friendly client-facing message, and is re-validated inside the service, row-locked,
    against what is actually persisted (see `replace_categories`) — the schema check alone
    can't protect against a concurrent sibling-category edit changing the sum between request
    and write.

    Concurrency note: `DistributionCategory` is one of the entities D-018 lists for
    optimistic-locking, but categories here are never mutated in isolation — they only ever
    change as a full set via `replace_categories`, which takes a pessimistic row lock
    (`SELECT ... FOR UPDATE`) on the parent rule for the whole operation. That lock is strictly
    stronger than an optimistic per-category check for this call path (it also protects the
    100% invariant across siblings, which a per-row check cannot), so it subsumes D-018's intent
    here rather than duplicating it with a second, weaker mechanism.
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

    # ------------------------------------------------------------------ update rule fields

    def update_rule(
        self, user: User, rule_id: uuid.UUID, payload: DistributionRuleUpdate
    ) -> DistributionRule:
        rule = self.repo.lock_rule_for_update(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Distribution rule not found.")
        if rule.updated_at != payload.expected_updated_at:
            raise ConflictError(
                "This distribution rule was modified by another request. Reload and try again."
            )
        if (
            payload.name is None
            and payload.description is None
            and payload.is_active is None
            and payload.is_default is None
        ):
            raise ValidationAppError("No fields provided to update.")

        before = {
            "name": rule.name,
            "description": rule.description,
            "is_active": rule.is_active,
            "is_default": rule.is_default,
        }

        if payload.is_active is False and rule.is_active is True:
            if self.repo.is_rule_selected_by_open_period(user.id, rule.id):
                raise ConflictError(
                    "Cannot deactivate a distribution rule that is the active selection for "
                    "an open financial period. Select a different rule for that period first."
                )

        # Unset-then-set avoids ever tripping the partial unique index on is_default (D-010-style
        # handling, applied here to DistributionRule.is_default per D-009's default-rule slot).
        if payload.is_default is True and not rule.is_default:
            self.repo.unset_other_defaults(user.id, except_rule_id=rule.id)
            rule.is_default = True
        elif payload.is_default is False:
            rule.is_default = False

        if payload.name is not None:
            rule.name = payload.name
        if payload.description is not None:
            rule.description = payload.description
        if payload.is_active is not None:
            rule.is_active = payload.is_active

        self.repo.save_rule(rule)

        self.audit.record(
            user_id=user.id,
            entity_type="DistributionRule",
            entity_id=rule.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": rule.name,
                "description": rule.description,
                "is_active": rule.is_active,
                "is_default": rule.is_default,
            },
        )
        self.db.commit()
        return self.get_rule(user, rule.id)

    # ------------------------------------------------------------------ replace categories

    def replace_categories(
        self, user: User, rule_id: uuid.UUID, payload: DistributionCategoriesReplace
    ) -> DistributionRule:
        rule = self.repo.lock_rule_for_update(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Distribution rule not found.")
        if rule.updated_at != payload.expected_updated_at:
            raise ConflictError(
                "This distribution rule was modified by another request. Reload and try again."
            )

        existing = {cat.id: cat for cat in self.repo.list_categories(rule.id)}
        incoming_ids = {item.id for item in payload.categories if item.id is not None}

        unknown_ids = incoming_ids - set(existing.keys())
        if unknown_ids:
            raise ValidationAppError(
                f"Unknown category id(s) for this rule: {sorted(str(u) for u in unknown_ids)}"
            )

        to_remove = [cat for cat_id, cat in existing.items() if cat_id not in incoming_ids]
        for cat in to_remove:
            if self.repo.is_category_referenced_by_expenses(cat.id):
                raise ConflictError(
                    f"Cannot remove category '{cat.name}': it is still referenced by existing "
                    "expenses. Reassign or delete those expenses first."
                )

        # Clear the unallocated-bucket slot before reassigning so moving the flag between
        # categories never collides with the partial unique index mid-transaction (D-010).
        self.repo.reset_unallocated_flags(rule.id)

        for cat in to_remove:
            self.repo.delete_category(cat)

        for item in payload.categories:
            if item.id is not None:
                target = existing[item.id]
                target.name = item.name
                target.percentage = item.percentage
                target.contributes_to_automatic_savings = item.contributes_to_automatic_savings
                target.is_unallocated_bucket = item.is_unallocated_bucket
                target.display_order = item.display_order
                self.repo.save_category(target)
            else:
                self.repo.add_category(
                    DistributionCategory(
                        distribution_rule_id=rule.id,
                        name=item.name,
                        percentage=item.percentage,
                        contributes_to_automatic_savings=item.contributes_to_automatic_savings,
                        is_unallocated_bucket=item.is_unallocated_bucket,
                        display_order=item.display_order,
                    )
                )

        self.db.flush()

        # Re-validate the 100% invariant against what is actually persisted, while the parent
        # rule row lock is still held — this is precisely the race the lock exists to close
        # (D-009): a concurrent request editing sibling categories can't commit in between our
        # read and this check, because it would be blocked on the same row lock until we commit.
        final_categories = self.repo.list_categories(rule.id)
        total = sum((Decimal(cat.percentage) for cat in final_categories), Decimal("0"))
        if total != HUNDRED:
            raise ValidationAppError(
                f"Distribution category percentages must sum to exactly 100%, got {total}."
            )

        # No column on `rule` itself was necessarily touched by a categories-only edit, so bump
        # updated_at explicitly — it is the client-facing token for "has this rule's
        # categories changed since I last read them" (D-018-style convention, extended to cover
        # the aggregate, not just the row's own scalar columns).
        rule.updated_at = datetime.now(timezone.utc)
        self.repo.save_rule(rule)

        self.audit.record(
            user_id=user.id,
            entity_type="DistributionRule",
            entity_id=rule.id,
            action="UPDATE_CATEGORIES",
            after_state={
                "category_count": len(final_categories),
                "total_percentage": str(total),
            },
        )
        self.db.commit()
        return self.get_rule(user, rule.id)

    # ------------------------------------------------------------------ soft-delete / deactivate

    def deactivate_rule(self, user: User, rule_id: uuid.UUID) -> None:
        """Soft-deletes (retires) a rule. Blocked if the rule is the active
        `distribution_rule_id` selection for any OPEN period of this user's — a closed period's
        frozen summary doesn't care, but an open period actively relying on this rule to compute
        category allocations would otherwise silently lose its rule out from under it."""
        rule = self.get_rule(user, rule_id)
        if self.repo.is_rule_selected_by_open_period(user.id, rule.id):
            raise ConflictError(
                "Cannot delete a distribution rule that is the active selection for an open "
                "financial period. Select a different rule for that period first."
            )

        before = {"is_active": rule.is_active, "is_default": rule.is_default}
        rule.is_active = False
        rule.is_default = False
        rule.deleted_at = datetime.now(timezone.utc)
        self.repo.save_rule(rule)

        self.audit.record(
            user_id=user.id,
            entity_type="DistributionRule",
            entity_id=rule.id,
            action="DELETE",
            before_state=before,
        )
        self.db.commit()
