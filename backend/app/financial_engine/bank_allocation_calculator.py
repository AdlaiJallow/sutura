"""Savings-to-account allocation helpers (spec §19/§20, D-014).

Never lets bank/savings allocation exceed available Final Savings — callers must check
`would_exceed_available` (or use `apply_percentage_rule`, which never over-allocates by
construction) before persisting a SavingsAllocation row.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.financial_engine.rounding import quantize_money

HUNDRED = Decimal("100")


def would_exceed_available(
    *, already_allocated: Decimal, new_amount: Decimal, final_savings_total: Decimal
) -> bool:
    return (Decimal(already_allocated) + Decimal(new_amount)) > Decimal(final_savings_total)


@dataclass(frozen=True)
class RuleItemInput:
    key: object  # bank_account_id or destination_label
    percentage: Decimal


@dataclass(frozen=True)
class AllocationResult:
    key: object
    amount: Decimal


def apply_percentage_rule(
    *, amount_to_distribute: Decimal, rule_items: Iterable[RuleItemInput]
) -> list[AllocationResult]:
    """Splits `amount_to_distribute` across rule items by percentage. The last item absorbs any
    residual cent from rounding, so the sum of results always equals the input exactly (never
    over- or under-allocates due to rounding drift).
    """
    items = list(rule_items)
    results: list[AllocationResult] = []
    running_total = Decimal("0")
    amount = Decimal(amount_to_distribute)

    for index, item in enumerate(items):
        if index == len(items) - 1:
            share = amount - running_total
        else:
            share = quantize_money(amount * Decimal(item.percentage) / HUNDRED)
            running_total += share
        results.append(AllocationResult(key=item.key, amount=quantize_money(share)))

    return results
