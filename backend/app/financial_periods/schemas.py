import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FinancialPeriodCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class FinancialPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    year: int
    month: int
    start_date: date
    end_date: date
    status: str
    distribution_rule_id: uuid.UUID | None
    base_currency: str
    closed_at: datetime | None
    closed_by: uuid.UUID | None
    reopened_count: int
    last_reopened_at: datetime | None


class FinancialPeriodPatch(BaseModel):
    notes: str | None = None


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class SelectDistributionRuleRequest(BaseModel):
    distribution_rule_id: uuid.UUID


class MonthlySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    financial_period_id: uuid.UUID
    version: int
    is_current: bool
    total_salary_income: Decimal
    total_allowances: Decimal
    total_other_income: Decimal
    total_monthly_income: Decimal
    total_expenses: Decimal
    total_planned_savings: Decimal
    automatic_savings: Decimal
    manual_savings: Decimal
    final_savings: Decimal
    total_bank_deposits: Decimal
    undistributed_savings: Decimal
    triggered_by: str
    calculated_at: datetime
