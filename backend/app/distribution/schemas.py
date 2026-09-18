import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class DistributionRuleCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None
    categories: list[DistributionCategoryCreate]

    @field_validator("categories")
    @classmethod
    def must_sum_to_100(
        cls, categories: list[DistributionCategoryCreate]
    ) -> list[DistributionCategoryCreate]:
        if not categories:
            raise ValueError("At least one category is required.")
        total = sum((c.percentage for c in categories), Decimal("0"))
        if total != Decimal("100.00"):
            raise ValueError(
                f"Distribution category percentages must sum to exactly 100%, got {total}."
            )
        return categories


class DistributionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    is_default: bool
    categories: list[DistributionCategoryRead] = []
