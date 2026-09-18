import uuid
from datetime import date
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
