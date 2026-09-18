import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_percentage_invariants(categories: list) -> list:
    """Shared by create and replace-categories schemas (D-009/D-010): percentages must sum to
    exactly 100.00, and at most one category may be flagged as the unallocated bucket (the
    partial unique index is the DB-level backstop; this is the friendly client-facing check)."""
    if not categories:
        raise ValueError("At least one category is required.")
    total = sum((c.percentage for c in categories), Decimal("0"))
    if total != Decimal("100.00"):
        raise ValueError(
            f"Distribution category percentages must sum to exactly 100%, got {total}."
        )
    unallocated_count = sum(1 for c in categories if c.is_unallocated_bucket)
    if unallocated_count > 1:
        raise ValueError("At most one category may be flagged as the unallocated bucket.")
    return categories


class DistributionCategoryCreate(BaseModel):
    name: str = Field(max_length=100)
    percentage: Decimal
    contributes_to_automatic_savings: bool = True
    is_unallocated_bucket: bool = False
    display_order: int = 0


class DistributionCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    percentage: Decimal
    contributes_to_automatic_savings: bool
    is_unallocated_bucket: bool
    display_order: int


class DistributionCategoryUpsert(BaseModel):
    """Used by the replace-categories endpoint. `id` present + matching an existing category
    on the rule => update in place; `id` omitted/null => a new category is created. Any
    existing category whose id is *not* present in the submitted list is removed."""

    id: uuid.UUID | None = None
    name: str = Field(max_length=100)
    percentage: Decimal
    contributes_to_automatic_savings: bool = True
    is_unallocated_bucket: bool = False
    display_order: int = 0


class DistributionRuleCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None
    categories: list[DistributionCategoryCreate]

    @field_validator("categories")
    @classmethod
    def must_sum_to_100(
        cls, categories: list[DistributionCategoryCreate]
    ) -> list[DistributionCategoryCreate]:
        return _validate_percentage_invariants(categories)


class DistributionRuleUpdate(BaseModel):
    """Partial update of a rule's own fields (not its categories — see
    DistributionCategoriesReplace for that). `expected_updated_at` is the D-018-style
    optimistic-locking token, checked after acquiring the row lock (belt-and-braces on top of
    the pessimistic lock used for the actual mutation)."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    expected_updated_at: datetime


class DistributionCategoriesReplace(BaseModel):
    categories: list[DistributionCategoryUpsert]
    expected_updated_at: datetime

    @field_validator("categories")
    @classmethod
    def must_sum_to_100(
        cls, categories: list[DistributionCategoryUpsert]
    ) -> list[DistributionCategoryUpsert]:
        return _validate_percentage_invariants(categories)


class DistributionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    is_default: bool
    categories: list[DistributionCategoryRead] = []
    updated_at: datetime
