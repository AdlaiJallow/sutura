"""Unit tests for the canonical income formulas (CLAUDE.md / spec §26)."""
from decimal import Decimal

from app.financial_engine.income_calculator import (
    total_allowances,
    total_monthly_income,
    total_other_income,
    total_salary_income,
)


def test_total_allowances_sums_all_allowances():
    result = total_allowances([Decimal("2000"), Decimal("1000")])
    assert result == Decimal("3000.0000")


def test_total_allowances_empty_is_zero():
    assert total_allowances([]) == Decimal("0.0000")


def test_total_salary_income_adds_net_salary_and_allowances():
    result = total_salary_income(Decimal("10000"), Decimal("3000"))
    assert result == Decimal("13000.0000")


def test_total_other_income_sums_income_records():
    result = total_other_income([Decimal("500"), Decimal("500")])
    assert result == Decimal("1000.0000")


def test_total_monthly_income_adds_salary_income_and_other_income():
    result = total_monthly_income(Decimal("13000"), Decimal("1000"))
    assert result == Decimal("14000.0000")


def test_zero_income_edge_case():
    """Edge case §38: zero income — every downstream figure must be exactly zero, not an error."""
    salary_income = total_salary_income(Decimal("0"), total_allowances([]))
    monthly_income = total_monthly_income(salary_income, total_other_income([]))
    assert monthly_income == Decimal("0.0000")
