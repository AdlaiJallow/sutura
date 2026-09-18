"""Canonical income formulas (CLAUDE.md / spec §26). Pure Decimal functions, no I/O.

    Total Allowances    = SUM(Allowances)
    Total Salary Income = Net Salary + Total Allowances
    Total Monthly Income = Total Salary Income + Other Income
"""
from decimal import Decimal
from typing import Iterable

from app.financial_engine.rounding import quantize_money


def total_allowances(allowance_amounts: Iterable[Decimal]) -> Decimal:
    total = sum(allowance_amounts, Decimal("0"))
    return quantize_money(Decimal(total))


def total_salary_income(net_salary: Decimal, allowances_total: Decimal) -> Decimal:
    return quantize_money(Decimal(net_salary) + Decimal(allowances_total))


def total_monthly_income(salary_income_total: Decimal, other_income_total: Decimal) -> Decimal:
    return quantize_money(Decimal(salary_income_total) + Decimal(other_income_total))


def total_other_income(income_amounts: Iterable[Decimal]) -> Decimal:
    total = sum(income_amounts, Decimal("0"))
    return quantize_money(Decimal(total))
