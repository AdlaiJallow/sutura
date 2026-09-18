import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

INCOME_TYPES = {"IN_COUNTRY_PAYMENT", "PER_DIEM", "FREELANCE", "BUSINESS", "INVESTMENT", "OTHER"}


class IncomeCreate(BaseModel):
    financial_period_id: uuid.UUID
    income_type: str
    description: str = Field(max_length=255)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    date_received: date
    source: str | None = Field(default=None, max_length=150)
    is_recurring: bool = False
    notes: str | None = None

    @field_validator("income_type")
    @classmethod
    def valid_income_type(cls, value: str) -> str:
        if value not in INCOME_TYPES:
            raise ValueError(
                f"income_type must be one of {sorted(INCOME_TYPES)} "
                "(salary/allowances are recorded via their own endpoints, D-007)."
            )
        return value


class IncomeUpdate(BaseModel):
    """Partial update; `expected_updated_at` is the D-018 optimistic-locking token."""

    income_type: str | None = None
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    date_received: date | None = None
    source: str | None = Field(default=None, max_length=150)
    is_recurring: bool | None = None
    notes: str | None = None
    expected_updated_at: datetime

    @field_validator("income_type")
    @classmethod
    def valid_income_type(cls, value: str | None) -> str | None:
        if value is not None and value not in INCOME_TYPES:
            raise ValueError(
                f"income_type must be one of {sorted(INCOME_TYPES)} "
                "(salary/allowances are recorded via their own endpoints, D-007)."
            )
        return value


class IncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    income_type: str
    description: str
    amount: Decimal
    currency: str
    date_received: date
    source: str | None
    is_recurring: bool
    notes: str | None
    updated_at: datetime
