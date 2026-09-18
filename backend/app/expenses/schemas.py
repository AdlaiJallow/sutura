import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    financial_period_id: uuid.UUID
    distribution_category_id: uuid.UUID | None = None
    name: str = Field(max_length=150)
    expense_category: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    expense_date: date
    payment_method: str | None = None
    bank_account_id: uuid.UUID | None = None
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    """Partial update; `expected_updated_at` is the D-018 optimistic-locking token.
    `distribution_category_id` may be explicitly set to `null` to clear it; whatever the
    resulting value is (changed or not), the service re-validates it against the owning
    period's selected distribution rule (D-006 ERD note)."""

    distribution_category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=150)
    expense_category: str | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    expense_date: date | None = None
    payment_method: str | None = None
    bank_account_id: uuid.UUID | None = None
    notes: str | None = None
    expected_updated_at: datetime


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    distribution_category_id: uuid.UUID | None
    name: str
    expense_category: str
    amount: Decimal
    currency: str
    expense_date: date
    payment_method: str | None
    bank_account_id: uuid.UUID | None
    notes: str | None
    updated_at: datetime
