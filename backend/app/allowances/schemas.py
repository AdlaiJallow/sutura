import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AllowanceCreate(BaseModel):
    financial_period_id: uuid.UUID
    name: str = Field(max_length=100)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    is_recurring: bool = False
    date_received: date
    notes: str | None = None


class AllowanceUpdate(BaseModel):
    """Partial update; `expected_updated_at` is the D-018 optimistic-locking token."""

    name: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_recurring: bool | None = None
    date_received: date | None = None
    notes: str | None = None
    expected_updated_at: datetime


class AllowanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    name: str
    amount: Decimal
    currency: str
    is_recurring: bool
    date_received: date
    notes: str | None
    updated_at: datetime
