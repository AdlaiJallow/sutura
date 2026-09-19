import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Mirrors the DB CHECK constraints on `expenses` exactly (app/expenses/models.py) — validated
# here too so an invalid value is a clean 422, not a raw IntegrityError/500 (the same fix
# already applied to income_type, D-007's sibling field elsewhere).
EXPENSE_CATEGORIES = {
    "RENT", "FOOD", "TRANSPORTATION", "ELECTRICITY", "WATER", "INTERNET", "PHONE",
    "EDUCATION", "HEALTHCARE", "FAMILY_SUPPORT", "ENTERTAINMENT", "SHOPPING",
    "DEBT_REPAYMENT", "OTHER",
}
PAYMENT_METHODS = {"CASH", "BANK_TRANSFER", "CARD", "MOBILE_MONEY", "OTHER"}


def _valid_expense_category(value: str | None) -> str | None:
    if value is not None and value not in EXPENSE_CATEGORIES:
        raise ValueError(f"expense_category must be one of {sorted(EXPENSE_CATEGORIES)}.")
    return value


def _valid_payment_method(value: str | None) -> str | None:
    if value is not None and value not in PAYMENT_METHODS:
        raise ValueError(f"payment_method must be one of {sorted(PAYMENT_METHODS)}.")
    return value


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

    _validate_expense_category = field_validator("expense_category")(_valid_expense_category)
    _validate_payment_method = field_validator("payment_method")(_valid_payment_method)


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

    _validate_expense_category = field_validator("expense_category")(_valid_expense_category)
    _validate_payment_method = field_validator("payment_method")(_valid_payment_method)


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
