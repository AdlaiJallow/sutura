"""Rounding edge cases (CLAUDE.md rule 9 — test rounding explicitly; D-019 quantization)."""
from decimal import Decimal

from app.financial_engine.distribution_calculator import category_allocation
from app.financial_engine.rounding import quantize_money


def test_quantize_money_rounds_half_up_at_4dp():
    assert quantize_money(Decimal("10.00005")) == Decimal("10.0001")
    assert quantize_money(Decimal("10.000049")) == Decimal("10.0000")


def test_category_allocation_percentage_that_does_not_divide_evenly():
    """A percentage split of an income figure that does not divide evenly across 3dp must still
    quantize deterministically to 4dp rather than losing precision or raising."""
    result = category_allocation(Decimal("1000.00"), Decimal("33.33"))
    assert result == Decimal("333.3000")


def test_quantize_money_handles_negative_values_for_overspend():
    assert quantize_money(Decimal("-200.00005")) == Decimal("-200.0001")
