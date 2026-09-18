import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SalaryCreate(BaseModel):
    financial_period_id: uuid.UUID
    net_amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: str = "RECEIVED"
    notes: str | None = None


class SalaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    net_amount: Decimal
    currency: str
    status: str
    notes: str | None
    is_recurring_generated: bool
