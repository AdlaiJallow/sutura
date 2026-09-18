"""Canonical savings formulas (CLAUDE.md / spec §26, D-001, D-012):

    Automatic Savings     = SUM(Eligible Positive Category Remaining Values)
    Final Savings         = Automatic Savings + Manual Savings
    Undistributed Savings = Final Savings - Savings Distributed

Eligibility (D-001) is a per-category boolean (`contributes_to_automatic_savings`), never a
hardcoded category-name check. Only *positive* remainders from *eligible* categories are summed —
negative remainders (overspend) are never subtracted from automatic savings.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.financial_engine.rounding import quantize_money

ZERO = Decimal("0")


@dataclass(frozen=True)
class CategoryRemainderInput:
    remaining: Decimal
    contributes_to_automatic_savings: bool


def automatic_savings(category_remainders: Iterable[CategoryRemainderInput]) -> Decimal:
    total = ZERO
    for item in category_remainders:
        remaining = Decimal(item.remaining)
        if item.contributes_to_automatic_savings and remaining > ZERO:
            total += remaining
    return quantize_money(total)


def manual_savings_total(savings_item_amounts: Iterable[Decimal]) -> Decimal:
    total = sum(savings_item_amounts, ZERO)
    return quantize_money(Decimal(total))


def final_savings(automatic: Decimal, manual: Decimal) -> Decimal:
    return quantize_money(Decimal(automatic) + Decimal(manual))


def undistributed_savings(final: Decimal, distributed: Decimal) -> Decimal:
    return quantize_money(Decimal(final) - Decimal(distributed))
