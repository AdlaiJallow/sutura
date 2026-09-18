"""Assembles a full MonthlyFinancialSummary snapshot from already-computed Decimal figures.
This function does not fetch anything itself — the caller (financial_periods service) is
responsible for gathering every input via its repositories."""
from dataclasses import dataclass
from decimal import Decimal

from app.financial_engine.income_calculator import total_monthly_income, total_salary_income
from app.financial_engine.rounding import quantize_money
from app.financial_engine.savings_calculator import final_savings


@dataclass(frozen=True)
class MonthlySummaryInputs:
    net_salary: Decimal
    total_allowances: Decimal
    total_other_income: Decimal
    total_expenses: Decimal
    total_planned_savings: Decimal
    automatic_savings: Decimal
    manual_savings: Decimal
    total_bank_deposits: Decimal
    distributed_savings: Decimal


@dataclass(frozen=True)
class MonthlySummaryResult:
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


def build_monthly_summary(inputs: MonthlySummaryInputs) -> MonthlySummaryResult:
    salary_income = total_salary_income(inputs.net_salary, inputs.total_allowances)
    monthly_income = total_monthly_income(salary_income, inputs.total_other_income)
    final = final_savings(inputs.automatic_savings, inputs.manual_savings)
    undistributed = quantize_money(final - Decimal(inputs.distributed_savings))

    return MonthlySummaryResult(
        total_salary_income=salary_income,
        total_allowances=quantize_money(Decimal(inputs.total_allowances)),
        total_other_income=quantize_money(Decimal(inputs.total_other_income)),
        total_monthly_income=monthly_income,
        total_expenses=quantize_money(Decimal(inputs.total_expenses)),
        total_planned_savings=quantize_money(Decimal(inputs.total_planned_savings)),
        automatic_savings=quantize_money(Decimal(inputs.automatic_savings)),
        manual_savings=quantize_money(Decimal(inputs.manual_savings)),
        final_savings=final,
        total_bank_deposits=quantize_money(Decimal(inputs.total_bank_deposits)),
        undistributed_savings=undistributed,
    )
