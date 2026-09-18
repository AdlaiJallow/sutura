import uuid
from datetime import date, datetime
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
