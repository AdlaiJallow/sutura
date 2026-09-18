import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BankTransactionCreate(BaseModel):
    bank_account_id: uuid.UUID
    financial_period_id: uuid.UUID
    transaction_type: str = Field(description="DEPOSIT|WITHDRAWAL|ADJUSTMENT")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    transaction_date: date
    description: str | None = None


class BankTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_account_id: uuid.UUID
    financial_period_id: uuid.UUID
    transaction_type: str
    amount: Decimal
    currency: str
    transaction_date: date
    description: str | None
    related_record_type: str | None
    related_record_id: uuid.UUID | None
    transfer_pair_id: uuid.UUID | None


class BankTransferCreate(BaseModel):
    source_bank_account_id: uuid.UUID
    destination_bank_account_id: uuid.UUID
    financial_period_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    transaction_date: date
    description: str | None = None


class BankTransferRead(BaseModel):
    transfer_pair_id: uuid.UUID
    source_transaction: BankTransactionRead
    destination_transaction: BankTransactionRead
