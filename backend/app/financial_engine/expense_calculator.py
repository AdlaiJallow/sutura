"""Expense aggregation helpers. `total_expenses` never double-counts across categories — it is a
straight sum over already-fetched Expense rows for a period (D-006)."""
from collections import defaultdict
from decimal import Decimal
from typing import Iterable, NamedTuple

from app.financial_engine.rounding import quantize_money


def total_expenses(expense_amounts: Iterable[Decimal]) -> Decimal:
    total = sum(expense_amounts, Decimal("0"))
    return quantize_money(Decimal(total))


class ExpenseRow(NamedTuple):
    expense_category: str
    amount: Decimal


def spending_by_category(expenses: Iterable[ExpenseRow]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in expenses:
        totals[row.expense_category] += Decimal(row.amount)
    return {category: quantize_money(amount) for category, amount in totals.items()}
