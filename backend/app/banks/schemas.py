import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BankAccountCreate(BaseModel):
    account_name: str = Field(max_length=100)
    institution_name: str | None = Field(default=None, max_length=100)
    account_type: str | None = None
    account_identifier: str | None = Field(default=None, description="Raw identifier, encrypted server-side, never echoed back in full")
    currency: str = Field(default="GMD", min_length=3, max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)


class BankAccountUpdate(BaseModel):
    """Partial update; `expected_updated_at` is the D-018 optimistic-locking token.

    `account_identifier`, when supplied, is re-derived into `account_identifier_last4` the same
    way `create()` does (§17/§34) — the raw value is never persisted or echoed back. Also used
    to reactivate a deactivated account (`is_active: true`)."""

    account_name: str | None = Field(default=None, max_length=100)
    institution_name: str | None = Field(default=None, max_length=100)
    account_type: str | None = None
    account_identifier: str | None = Field(
        default=None, description="Raw identifier, encrypted server-side, never echoed back in full"
    )
    notes: str | None = None
    is_active: bool | None = None
    expected_updated_at: datetime


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
    notes: str | None
    updated_at: datetime
