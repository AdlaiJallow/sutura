import uuid
from datetime import date
from datetime import date as _Date  # noqa: N812 -- see SavingsItemUpdate.date below
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
