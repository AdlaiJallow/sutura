import uuid
from datetime import date
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
