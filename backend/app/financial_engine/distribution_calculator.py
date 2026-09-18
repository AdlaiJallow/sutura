"""Canonical distribution formulas (CLAUDE.md / spec §26):

    Category Allocation = Total Monthly Income * Category Percentage
    Category Used        = SUM(Category Items)
    Category Remaining   = Category Allocation - Category Used

`percentage` is a whole-percent value (e.g. Decimal("50.00") means 50%), matching the
NUMERIC(5,2) column — never a 0-1 fraction.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.financial_engine.rounding import quantize_money

HUNDRED = Decimal("100")


def category_allocation(total_monthly_income: Decimal, percentage: Decimal) -> Decimal:
    return quantize_money(Decimal(total_monthly_income) * Decimal(percentage) / HUNDRED)


def category_used(item_amounts: Iterable[Decimal]) -> Decimal:
    total = sum(item_amounts, Decimal("0"))
    return quantize_money(Decimal(total))


def category_remaining(allocation: Decimal, used: Decimal) -> Decimal:
    return quantize_money(Decimal(allocation) - Decimal(used))


def is_overspent(remaining: Decimal) -> bool:
    return Decimal(remaining) < Decimal("0")


@dataclass(frozen=True)
class CategoryDistributionResult:
    category_id: object
    allocation: Decimal
    used: Decimal
    remaining: Decimal
    is_overspent: bool
    contributes_to_automatic_savings: bool


def compute_category_distribution(
    *,
    category_id: object,
    total_monthly_income: Decimal,
    percentage: Decimal,
    item_amounts: Iterable[Decimal],
    contributes_to_automatic_savings: bool,
) -> CategoryDistributionResult:
    allocation = category_allocation(total_monthly_income, percentage)
    used = category_used(item_amounts)
    remaining = category_remaining(allocation, used)
    return CategoryDistributionResult(
        category_id=category_id,
        allocation=allocation,
        used=used,
        remaining=remaining,
        is_overspent=is_overspent(remaining),
        contributes_to_automatic_savings=contributes_to_automatic_savings,
    )
