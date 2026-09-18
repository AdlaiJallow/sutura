import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.banks.repository import BankAccountRepository
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.financial_engine.bank_allocation_calculator import (
    AllocationResult,
    RuleItemInput,
    apply_percentage_rule,
    would_exceed_available,
)
from app.financial_periods.repository import FinancialPeriodRepository
from app.financial_periods.service import FinancialPeriodService
from app.savings.models import (
    Savings,
    SavingsAllocation,
    SavingsDistributionRule,
    SavingsDistributionRuleItem,
    SavingsItem,
)
from app.savings.repository import (
    SavingsAllocationRepository,
    SavingsDistributionRuleRepository,
    SavingsItemRepository,
    SavingsRepository,
)
from app.savings.schemas import (
    SavingsAllocationCreate,
    SavingsDistributionRuleCreate,
    SavingsDistributionRuleItemsReplace,
    SavingsDistributionRuleUpdate,
    SavingsItemCreate,
    SavingsItemUpdate,
)
from app.transactions.models import BankTransaction
from app.transactions.repository import BankTransactionRepository
from app.users.models import User

HUNDRED = Decimal("100.00")


class SavingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsRepository(db)
        self.periods = FinancialPeriodRepository(db)

    def get_for_period(self, user: User, period_id: uuid.UUID) -> Savings:
        period = self.periods.get_owned(user.id, period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        row = self.repo.get_for_period(user.id, period_id)
        if row is not None:
            return row
        # No calculation has run yet (e.g. a brand-new period) — synthesize a zeroed view
        # rather than 404, since the period itself is real. financial_periods.get_summary
        # performs the authoritative recalculation.
        return Savings(
            id=uuid.uuid4(),
            user_id=user.id,
            financial_period_id=period_id,
            automatic_savings_computed=Decimal("0"),
            manual_savings_total=Decimal("0"),
            final_savings_total=Decimal("0"),
            distributed_total=Decimal("0"),
            undistributed_total=Decimal("0"),
            last_calculated_at=None,
        )


class SavingsItemService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsItemRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.savings = SavingsRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: SavingsItemCreate) -> SavingsItem:
        self._ensure_period_open(user, payload.financial_period_id)
        savings_row = self.savings.get_for_period(user.id, payload.financial_period_id)
        if savings_row is None:
            savings_row = Savings(
                user_id=user.id,
                financial_period_id=payload.financial_period_id,
                last_calculated_at=datetime.now(timezone.utc),
            )
            self.db.add(savings_row)
            self.db.flush()

        item = SavingsItem(
            user_id=user.id,
            financial_period_id=payload.financial_period_id,
            savings_id=savings_row.id,
            name=payload.name,
            amount=payload.amount,
            currency=payload.currency.upper(),
            date=payload.date,
            destination=payload.destination,
            notes=payload.notes,
        )
        self.repo.create(item)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=item.id,
            action="CREATE",
            after_state={"amount": str(item.amount)},
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        # NOTE: recalculating the Savings cache (automatic/final/undistributed) happens the
        # next time financial_periods.get_summary/close is called (D-012); a live trigger here
        # is Phase 3 wiring once the full distribution engine exists.
        return item

    def update(self, user: User, item_id: uuid.UUID, payload: SavingsItemUpdate) -> SavingsItem:
        item = self.get(user, item_id)
        self._ensure_period_open(user, item.financial_period_id)

        values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        if not values:
            raise ValidationAppError("No fields provided to update.")
        if values.get("currency"):
            values["currency"] = values["currency"].upper()

        before = {
            "name": item.name,
            "amount": str(item.amount),
            "currency": item.currency,
            "date": str(item.date),
            "destination": item.destination,
            "notes": item.notes,
        }

        rowcount = self.repo.update_owned(user.id, item_id, payload.expected_updated_at, values)
        if rowcount == 0:
            raise ConflictError(
                "This savings item was modified by another request. Reload and try again."
            )

        updated = self.get(user, item_id)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": updated.name,
                "amount": str(updated.amount),
                "currency": updated.currency,
                "date": str(updated.date),
                "destination": updated.destination,
                "notes": updated.notes,
            },
            related_record_type="FinancialPeriod",
            related_record_id=updated.financial_period_id,
        )
        self.db.commit()
        # NOTE: same as create() — the Savings cache recalculation happens the next time
        # financial_periods.get_summary/close runs (D-012), not synchronously here.
        return updated

    def get(self, user: User, item_id: uuid.UUID) -> SavingsItem:
        item = self.repo.get_owned(user.id, item_id)
        if item is None:
            raise NotFoundError("Savings item not found.")
        return item

    def list(
        self, user: User, financial_period_id: uuid.UUID | None, *, page: int, page_size: int
    ) -> tuple[list[SavingsItem], int]:
        return self.repo.list(user.id, financial_period_id=financial_period_id, page=page, page_size=page_size)

    def delete(self, user: User, item_id: uuid.UUID) -> None:
        item = self.get(user, item_id)
        self._ensure_period_open(user, item.financial_period_id)
        before = {"amount": str(item.amount)}
        self.repo.soft_delete(item)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsItem",
            entity_id=item.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=item.financial_period_id,
        )
        self.db.commit()


class SavingsDistributionRuleService:
    """Mirrors `app.distribution.service.DistributionService`'s maturity level (D-013): create
    (with items, 100%-sum validated at the schema layer, D-009-style), get, list, update rule
    fields (name/is_active/is_default with the unset-then-set default-swap pattern), and
    replace-items (row-locked on the parent rule, re-validated against what is actually
    persisted before committing)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsDistributionRuleRepository(db)
        self.accounts = BankAccountRepository(db)
        self.audit = AuditService(db)

    def _validate_item_bank_accounts(self, user: User, items: list) -> None:
        for item in items:
            if item.bank_account_id is None:
                continue
            account = self.accounts.get_owned(user.id, item.bank_account_id)
            if account is None:
                raise NotFoundError("Bank account not found.")
            if not account.is_active:
                raise ValidationAppError(
                    f"Bank account '{account.account_name}' is not active and cannot be used "
                    "as a savings distribution destination."
                )

    def create_rule(
        self, user: User, payload: SavingsDistributionRuleCreate
    ) -> SavingsDistributionRule:
        self._validate_item_bank_accounts(user, payload.items)
        rule = SavingsDistributionRule(user_id=user.id, name=payload.name)
        self.repo.create_rule(rule)
        for item in payload.items:
            self.repo.add_item(
                SavingsDistributionRuleItem(
                    savings_distribution_rule_id=rule.id,
                    bank_account_id=item.bank_account_id,
                    destination_label=item.destination_label,
                    percentage=item.percentage,
                )
            )
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsDistributionRule",
            entity_id=rule.id,
            action="CREATE",
            after_state={"name": rule.name, "item_count": len(payload.items)},
        )
        self.db.commit()
        return self.get_rule(user, rule.id)

    def get_rule(self, user: User, rule_id: uuid.UUID) -> SavingsDistributionRule:
        rule = self.repo.get_rule(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Savings distribution rule not found.")
        return rule

    def list_rules(
        self, user: User, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[SavingsDistributionRule], int]:
        return self.repo.list_rules(user.id, is_active=is_active, page=page, page_size=page_size)

    def update_rule(
        self, user: User, rule_id: uuid.UUID, payload: SavingsDistributionRuleUpdate
    ) -> SavingsDistributionRule:
        rule = self.repo.lock_rule_for_update(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Savings distribution rule not found.")
        if rule.updated_at != payload.expected_updated_at:
            raise ConflictError(
                "This savings distribution rule was modified by another request. Reload and "
                "try again."
            )
        if payload.name is None and payload.is_active is None and payload.is_default is None:
            raise ValidationAppError("No fields provided to update.")

        before = {
            "name": rule.name,
            "is_active": rule.is_active,
            "is_default": rule.is_default,
        }

        # Unset-then-set avoids ever tripping the partial unique index on is_default
        # (ux_savings_dist_rule_user_default), same convention as DistributionRule.is_default.
        if payload.is_default is True and not rule.is_default:
            self.repo.unset_other_defaults(user.id, except_rule_id=rule.id)
            rule.is_default = True
        elif payload.is_default is False:
            rule.is_default = False

        if payload.name is not None:
            rule.name = payload.name
        if payload.is_active is not None:
            rule.is_active = payload.is_active

        self.repo.save_rule(rule)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsDistributionRule",
            entity_id=rule.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "name": rule.name,
                "is_active": rule.is_active,
                "is_default": rule.is_default,
            },
        )
        self.db.commit()
        return self.get_rule(user, rule.id)

    def replace_items(
        self, user: User, rule_id: uuid.UUID, payload: SavingsDistributionRuleItemsReplace
    ) -> SavingsDistributionRule:
        rule = self.repo.lock_rule_for_update(user.id, rule_id)
        if rule is None:
            raise NotFoundError("Savings distribution rule not found.")
        if rule.updated_at != payload.expected_updated_at:
            raise ConflictError(
                "This savings distribution rule was modified by another request. Reload and "
                "try again."
            )
        self._validate_item_bank_accounts(user, payload.items)

        existing = {item.id: item for item in self.repo.list_items(rule.id)}
        incoming_ids = {item.id for item in payload.items if item.id is not None}
        unknown_ids = incoming_ids - set(existing.keys())
        if unknown_ids:
            raise ValidationAppError(
                f"Unknown item id(s) for this rule: {sorted(str(u) for u in unknown_ids)}"
            )

        to_remove = [item for item_id_, item in existing.items() if item_id_ not in incoming_ids]
        for item in to_remove:
            self.repo.delete_item(item)

        for item in payload.items:
            if item.id is not None:
                target = existing[item.id]
                target.bank_account_id = item.bank_account_id
                target.destination_label = item.destination_label
                target.percentage = item.percentage
                self.repo.save_item(target)
            else:
                self.repo.add_item(
                    SavingsDistributionRuleItem(
                        savings_distribution_rule_id=rule.id,
                        bank_account_id=item.bank_account_id,
                        destination_label=item.destination_label,
                        percentage=item.percentage,
                    )
                )

        self.db.flush()

        # Re-validate the 100% invariant against what is actually persisted, while the parent
        # rule row lock is still held (D-009-style), exactly mirroring
        # DistributionService.replace_categories.
        final_items = self.repo.list_items(rule.id)
        total = sum((Decimal(i.percentage) for i in final_items), Decimal("0"))
        if total != HUNDRED:
            raise ValidationAppError(
                f"Savings distribution item percentages must sum to exactly 100%, got {total}."
            )

        rule.updated_at = datetime.now(timezone.utc)
        self.repo.save_rule(rule)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsDistributionRule",
            entity_id=rule.id,
            action="UPDATE_ITEMS",
            after_state={"item_count": len(final_items), "total_percentage": str(total)},
        )
        self.db.commit()
        return self.get_rule(user, rule.id)


class SavingsAllocationService:
    """spec §19/§20/§28, D-014. Manual allocations optionally post a real `BankTransaction`
    (DEPOSIT) when `bank_account_id` is a real account; AUTO allocations generated by
    `apply_rule` never do (see that method's docstring for why — the append-only ledger, D-016,
    has no reversal path, which matters because `apply_rule` deletes-and-regenerates the AUTO
    set on every call)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SavingsAllocationRepository(db)
        self.savings_repo = SavingsRepository(db)
        self.rules_repo = SavingsDistributionRuleRepository(db)
        self.accounts = BankAccountRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.transactions = BankTransactionRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID):
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def _resolve_and_lock_savings(self, user: User, financial_period_id: uuid.UUID) -> Savings:
        """Ensures a persisted, *freshly recalculated* `Savings` cache row exists for this
        period by calling the existing (unmodified) `FinancialPeriodService.get_summary` — for
        an OPEN period this recomputes and commits the cache row from source records before we
        read it, so the over-allocation check below is never validated against a stale
        `final_savings_total` (D-012). The row is then locked `FOR UPDATE` for the remainder of
        the allocate-check-insert sequence (D-014/§19 concurrency guard)."""
        FinancialPeriodService(self.db).get_summary(user, financial_period_id)
        savings_row = self.savings_repo.get_for_period(user.id, financial_period_id)
        if savings_row is None:
            raise NotFoundError("Savings record not found for this period.")
        locked = self.savings_repo.lock_by_id(user.id, savings_row.id)
        if locked is None:
            raise NotFoundError("Savings record not found for this period.")
        return locked

    def create(self, user: User, payload: SavingsAllocationCreate) -> SavingsAllocation:
        self._ensure_period_open(user, payload.financial_period_id)
        savings_row = self._resolve_and_lock_savings(user, payload.financial_period_id)

        account = None
        if payload.bank_account_id is not None:
            account = self.accounts.get_owned(user.id, payload.bank_account_id)
            if account is None:
                raise NotFoundError("Bank account not found.")
            if not account.is_active:
                raise ValidationAppError("Cannot allocate savings to an inactive bank account.")

        amount = Decimal(payload.amount)
        already_allocated = Decimal(self.repo.sum_amount_for_savings(savings_row.id))
        if would_exceed_available(
            already_allocated=already_allocated,
            new_amount=amount,
            final_savings_total=Decimal(savings_row.final_savings_total),
        ):
            raise ConflictError(
                f"This allocation of {amount} would exceed available final savings "
                f"(final savings {Decimal(savings_row.final_savings_total)}, "
                f"{already_allocated} already allocated). Reduce the amount or reallocate "
                "first — allocations are never partially applied or silently clamped."
            )

        allocation = SavingsAllocation(
            user_id=user.id,
            savings_id=savings_row.id,
            bank_account_id=payload.bank_account_id,
            destination_label=payload.destination_label,
            amount=amount,
            allocation_method="MANUAL",
        )
        self.repo.create(allocation)

        if account is not None:
            txn = BankTransaction(
                user_id=user.id,
                bank_account_id=account.id,
                financial_period_id=payload.financial_period_id,
                transaction_type="DEPOSIT",
                amount=amount,
                currency=account.currency,
                transaction_date=payload.transaction_date or date.today(),
                description=f"Savings allocation to {account.account_name}",
                related_record_type="SAVINGS_ALLOCATION",
                related_record_id=allocation.id,
            )
            self.transactions.create(txn)
            account.current_balance = Decimal(account.current_balance) + amount
            self.accounts.save(account)
            allocation.bank_transaction_id = txn.id
            self.repo.save(allocation)

        self.audit.record(
            user_id=user.id,
            entity_type="SavingsAllocation",
            entity_id=allocation.id,
            action="CREATE",
            after_state={
                "amount": str(allocation.amount),
                "allocation_method": "MANUAL",
                "bank_account_id": str(account.id) if account else None,
                "destination_label": allocation.destination_label,
            },
            related_record_type="FinancialPeriod",
            related_record_id=payload.financial_period_id,
        )
        self.db.commit()
        return allocation

    def apply_rule(
        self, user: User, financial_period_id: uuid.UUID, savings_distribution_rule_id: uuid.UUID
    ) -> list[SavingsAllocation]:
        """Generates AUTO allocations from a SavingsDistributionRule's items.

        Judgment call #1 (explicitly requested — documented here, not silently decided):
        calling this again for the same period/savings_id **replaces** the previous AUTO
        allocations (bulk-deleted, never stacked) while any MANUAL allocations are left
        completely untouched. AUTO allocations never post a `BankTransaction`, even when an
        item's destination is a real `bank_account_id` — only the `create()` (manual) path does
        that. This is deliberate, not an oversight: `BankTransaction` is a strictly append-only
        ledger with no UPDATE/DELETE path (D-016) — a "replace" that had already posted deposits
        would have to fabricate offsetting ADJUSTMENT entries on every single regeneration just
        to keep the account balance correct, turning "preview/regenerate my savings split" into
        an operation that permanently grows the ledger. AUTO allocations are treated as a
        recomputable *plan* the user can freely regenerate; turning a plan into an actual ledger
        movement is what the manual `create()` action is for.

        The amount actually distributed is `final_savings_total - SUM(existing MANUAL amounts)`
        (never the full final_savings_total), so this can never push the combined
        MANUAL+AUTO total over `final_savings_total` (D-014) — if MANUAL allocations alone
        already exceed final savings, this is rejected outright rather than generating a
        negative/clamped split.
        """
        self._ensure_period_open(user, financial_period_id)
        savings_row = self._resolve_and_lock_savings(user, financial_period_id)

        rule = self.rules_repo.get_rule(user.id, savings_distribution_rule_id)
        if rule is None:
            raise NotFoundError("Savings distribution rule not found.")
        if not rule.items:
            raise ValidationAppError("This savings distribution rule has no items.")

        # Re-validate every item's bank account is still owned + active at apply time — a rule
        # can be created once and applied many times later, and an account referenced by it may
        # have been deactivated in the meantime (spec §38-32).
        for item in rule.items:
            if item.bank_account_id is None:
                continue
            account = self.accounts.get_owned(user.id, item.bank_account_id)
            if account is None:
                raise NotFoundError("Bank account not found.")
            if not account.is_active:
                raise ValidationAppError(
                    f"Bank account '{account.account_name}' referenced by this rule is no "
                    "longer active. Update the rule's items before applying it."
                )

        manual_rows, _ = self.repo.list_by_savings_id(
            user.id, savings_row.id, allocation_method="MANUAL", page=1, page_size=10_000
        )
        manual_total = sum((Decimal(r.amount) for r in manual_rows), Decimal("0"))

        amount_to_distribute = Decimal(savings_row.final_savings_total) - manual_total
        if amount_to_distribute < 0:
            raise ConflictError(
                "Manual allocations already exceed this period's final savings; cannot apply a "
                "distribution rule on top of them."
            )

        self.repo.delete_auto_for_savings(savings_row.id)
        self.db.flush()

        if amount_to_distribute == 0:
            self.audit.record(
                user_id=user.id,
                entity_type="SavingsDistributionRule",
                entity_id=rule.id,
                action="APPLY",
                after_state={"amount_distributed": "0", "allocations_created": 0},
                related_record_type="FinancialPeriod",
                related_record_id=financial_period_id,
            )
            self.db.commit()
            return []

        rule_items = [RuleItemInput(key=item.id, percentage=Decimal(item.percentage)) for item in rule.items]
        results: list[AllocationResult] = apply_percentage_rule(
            amount_to_distribute=amount_to_distribute, rule_items=rule_items
        )
        items_by_id = {item.id: item for item in rule.items}

        created: list[SavingsAllocation] = []
        for result in results:
            if result.amount <= 0:
                continue
            source_item = items_by_id[result.key]
            allocation = SavingsAllocation(
                user_id=user.id,
                savings_id=savings_row.id,
                bank_account_id=source_item.bank_account_id,
                destination_label=source_item.destination_label,
                amount=result.amount,
                allocation_method="AUTO",
            )
            self.repo.create(allocation)
            created.append(allocation)

        self.audit.record(
            user_id=user.id,
            entity_type="SavingsDistributionRule",
            entity_id=rule.id,
            action="APPLY",
            after_state={
                "amount_distributed": str(amount_to_distribute),
                "allocations_created": len(created),
            },
            related_record_type="FinancialPeriod",
            related_record_id=financial_period_id,
        )
        self.db.commit()
        return created

    def get(self, user: User, allocation_id: uuid.UUID) -> SavingsAllocation:
        allocation = self.repo.get_owned(user.id, allocation_id)
        if allocation is None:
            raise NotFoundError("Savings allocation not found.")
        return allocation

    def list(
        self,
        user: User,
        financial_period_id: uuid.UUID,
        *,
        allocation_method: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SavingsAllocation], int]:
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        savings_row = self.savings_repo.get_for_period(user.id, financial_period_id)
        if savings_row is None:
            return [], 0
        return self.repo.list_by_savings_id(
            user.id, savings_row.id, allocation_method=allocation_method, page=page, page_size=page_size
        )

    def delete(self, user: User, allocation_id: uuid.UUID) -> None:
        """Judgment call #2 (explicitly requested): an individual AUTO allocation cannot be
        deleted on its own — only `apply_rule` regenerates the AUTO set as a whole. AUTO rows
        exist to always mirror "the rule's current 100% split of what's left after MANUAL
        allocations"; deleting a single AUTO row would leave the remaining AUTO rows summing to
        less than the rule's intended 100% without it being obvious why, and would drift the set
        out of sync with the rule until the next `apply_rule` call anyway. MANUAL allocations,
        being individually user-created, are individually deletable while their period is open
        (mirrors the delete convention used for every other financial record in this codebase)."""
        allocation = self.get(user, allocation_id)
        if allocation.allocation_method != "MANUAL":
            raise ValidationAppError(
                "AUTO allocations cannot be deleted individually — call apply_rule again to "
                "regenerate the full set from the distribution rule."
            )
        savings_row = self.savings_repo.get_by_id(user.id, allocation.savings_id)
        if savings_row is None:
            raise NotFoundError("Savings record not found.")
        self._ensure_period_open(user, savings_row.financial_period_id)

        before = {
            "amount": str(allocation.amount),
            "bank_account_id": str(allocation.bank_account_id) if allocation.bank_account_id else None,
            "destination_label": allocation.destination_label,
        }
        # NOTE (documented, not a silently invented behavior): deleting a MANUAL allocation does
        # not reverse its linked BankTransaction, for the same append-only-ledger reason
        # apply_rule's AUTO-replacement never posts one in the first place (D-016). If the
        # linked deposit needs correcting, that is an explicit ADJUSTMENT transaction against
        # the bank account, posted separately — deleting the allocation record only removes it
        # from the savings-distribution bookkeeping, it is not a ledger operation.
        self.repo.delete(allocation)
        self.audit.record(
            user_id=user.id,
            entity_type="SavingsAllocation",
            entity_id=allocation.id,
            action="DELETE",
            before_state=before,
            related_record_type="FinancialPeriod",
            related_record_id=savings_row.financial_period_id,
        )
        self.db.commit()
