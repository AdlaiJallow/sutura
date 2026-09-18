import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SalaryCreate(BaseModel):
    financial_period_id: uuid.UUID
    net_amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: str = "RECEIVED"
    notes: str | None = None


class SalaryUpdate(BaseModel):
    """Partial update. `expected_updated_at` is the optimistic-locking token (D-018): the
    client must echo back the `updated_at` it last read from `SalaryRead`; a stale value is
    rejected with 409 rather than silently overwriting a concurrent change."""

    net_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: str | None = None
    notes: str | None = None
    expected_updated_at: datetime


class SalaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    net_amount: Decimal
    currency: str
    status: str
    notes: str | None
    is_recurring_generated: bool
    updated_at: datetime
