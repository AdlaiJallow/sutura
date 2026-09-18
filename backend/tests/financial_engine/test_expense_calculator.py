"""Unit tests for expense aggregation helpers (D-006 — no double counting)."""
from decimal import Decimal

from app.financial_engine.expense_calculator import ExpenseRow, spending_by_category, total_expenses


def test_total_expenses_sums_amounts():
    assert total_expenses([Decimal("6500"), Decimal("3900"), Decimal("2300")]) == Decimal("12700.0000")


def test_total_expenses_empty_is_zero():
    assert total_expenses([]) == Decimal("0.0000")


def test_spending_by_category_groups_correctly():
    rows = [
        ExpenseRow(expense_category="RENT", amount=Decimal("3000")),
        ExpenseRow(expense_category="FOOD", amount=Decimal("1500")),
        ExpenseRow(expense_category="FOOD", amount=Decimal("500")),
    ]
    result = spending_by_category(rows)
    assert result == {"RENT": Decimal("3000.0000"), "FOOD": Decimal("2000.0000")}
