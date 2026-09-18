import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BankAccountCreate(BaseModel):
    account_name: str = Field(max_length=100)
    institution_name: str | None = Field(default=None, max_length=100)
    account_type: str | None = None
    account_identifier: str | None = Field(default=None, description="Raw identifier, encrypted server-side, never echoed back in full")
    currency: str = Field(default="GMD", min_length=3, max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_name: str
    institution_name: str | None
    account_type: str | None
    account_identifier_last4: str | None
    currency: str
    opening_balance: Decimal
    current_balance: Decimal
    is_active: bool
