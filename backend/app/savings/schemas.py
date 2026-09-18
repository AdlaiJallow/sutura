import uuid
from datetime import date
from datetime import date as _Date  # noqa: N812 -- see SavingsItemUpdate.date below
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SavingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_period_id: uuid.UUID
    automatic_savings_computed: Decimal
    manual_savings_total: Decimal
    final_savings_total: Decimal
    distributed_total: Decimal
    undistributed_total: Decimal
    last_calculated_at: datetime | None


class SavingsItemCreate(BaseModel):
    financial_period_id: uuid.UUID
    name: str = Field(max_length=150)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    date: date
    destination: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class SavingsItemUpdate(BaseModel):
    """Partial update; `expected_updated_at` is the D-018 optimistic-locking token."""

    name: str | None = Field(default=None, max_length=150)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    # NOTE: aliased import (`_Date`) used here on purpose — a field literally named `date` with
    # a `= None` default, annotated as `date | None`, self-shadows the `date` type name once the
    # attribute is set on the class (observed under Python's lazy/deferred annotation
    # evaluation): by the time the annotation is resolved, `date` already refers to this field's
    # own `None` default instead of `datetime.date`, raising `TypeError` at import time.
    date: _Date | None = None
    destination: str | None = Field(default=None, max_length=150)
    notes: str | None = None
    expected_updated_at: datetime


class SavingsItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    name: str
    amount: Decimal
    currency: str
    date: date
    destination: str | None
    notes: str | None
    updated_at: datetime


# ---------------------------------------------------------------------------------------------
# SavingsDistributionRule / SavingsDistributionRuleItem (D-013) — parallel to
# app.distribution.schemas's DistributionRule schemas, adapted for savings-to-account splits.


def _require_destination(bank_account_id: uuid.UUID | None, destination_label: str | None) -> None:
    """Friendly, schema-level mirror of the DB `CHECK` constraint's intent
    (`ck_savings_dist_rule_item_destination` / `ck_savings_allocation_destination`): every item
    must reference either a real bank account or a free-text conceptual destination (D-014)."""
    if bank_account_id is None and not (destination_label and destination_label.strip()):
        raise ValueError(
            "Each item must reference either bank_account_id or a non-empty destination_label."
        )


def _validate_savings_percentage_sum(items: list) -> list:
    if not items:
        raise ValueError("At least one item is required.")
    total = sum((i.percentage for i in items), Decimal("0"))
    if total != Decimal("100.00"):
        raise ValueError(
            f"Savings distribution item percentages must sum to exactly 100%, got {total}."
        )
    return items


class SavingsDistributionRuleItemCreate(BaseModel):
    bank_account_id: uuid.UUID | None = None
    destination_label: str | None = Field(default=None, max_length=150)
    percentage: Decimal

    @model_validator(mode="after")
    def _check_destination(self) -> "SavingsDistributionRuleItemCreate":
        _require_destination(self.bank_account_id, self.destination_label)
        return self


class SavingsDistributionRuleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_account_id: uuid.UUID | None
    destination_label: str | None
    percentage: Decimal


class SavingsDistributionRuleItemUpsert(BaseModel):
    """Used by the replace-items endpoint. `id` present + matching an existing item on the rule
    => update in place; `id` omitted/null => a new item is created. Any existing item whose id is
    *not* present in the submitted list is removed (same convention as
    `DistributionCategoryUpsert`)."""

    id: uuid.UUID | None = None
    bank_account_id: uuid.UUID | None = None
    destination_label: str | None = Field(default=None, max_length=150)
    percentage: Decimal

    @model_validator(mode="after")
    def _check_destination(self) -> "SavingsDistributionRuleItemUpsert":
        _require_destination(self.bank_account_id, self.destination_label)
        return self


class SavingsDistributionRuleCreate(BaseModel):
    name: str = Field(max_length=100)
    items: list[SavingsDistributionRuleItemCreate]

    @field_validator("items")
    @classmethod
    def must_sum_to_100(
        cls, items: list[SavingsDistributionRuleItemCreate]
    ) -> list[SavingsDistributionRuleItemCreate]:
        return _validate_savings_percentage_sum(items)


class SavingsDistributionRuleUpdate(BaseModel):
    """Partial update of a rule's own fields (not its items — see
    SavingsDistributionRuleItemsReplace for that). `expected_updated_at` is the D-018-style
    optimistic-locking token, checked after acquiring the row lock."""

    name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    is_default: bool | None = None
    expected_updated_at: datetime


class SavingsDistributionRuleItemsReplace(BaseModel):
    items: list[SavingsDistributionRuleItemUpsert]
    expected_updated_at: datetime

    @field_validator("items")
    @classmethod
    def must_sum_to_100(
        cls, items: list[SavingsDistributionRuleItemUpsert]
    ) -> list[SavingsDistributionRuleItemUpsert]:
        return _validate_savings_percentage_sum(items)


class SavingsDistributionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    is_default: bool
    items: list[SavingsDistributionRuleItemRead] = []
    updated_at: datetime


# ---------------------------------------------------------------------------------------------
# SavingsAllocation (D-014, §19/§20)


class SavingsAllocationCreate(BaseModel):
    """Manual allocation. `financial_period_id` is resolved to the period's `Savings` cache row
    server-side (creating/refreshing it if needed) rather than requiring the client to already
    know the internal `savings_id` — consistent with every other create schema in this codebase
    keying off `financial_period_id`, not an internal aggregate row id."""

    financial_period_id: uuid.UUID
    bank_account_id: uuid.UUID | None = None
    destination_label: str | None = Field(default=None, max_length=150)
    amount: Decimal = Field(gt=0)
    transaction_date: date | None = Field(
        default=None,
        description="Date posted to the linked bank ledger entry when bank_account_id is a "
        "real account; defaults to today if omitted.",
    )

    @model_validator(mode="after")
    def _check_destination(self) -> "SavingsAllocationCreate":
        _require_destination(self.bank_account_id, self.destination_label)
        return self


class SavingsAllocationApplyRule(BaseModel):
    financial_period_id: uuid.UUID
    savings_distribution_rule_id: uuid.UUID


class SavingsAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    savings_id: uuid.UUID
    bank_account_id: uuid.UUID | None
    destination_label: str | None
    amount: Decimal
    allocation_method: str
    bank_transaction_id: uuid.UUID | None
    updated_at: datetime
