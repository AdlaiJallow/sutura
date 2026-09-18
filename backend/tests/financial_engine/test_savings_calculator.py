"""Unit tests for savings formulas (CLAUDE.md / spec §26, D-001)."""
from decimal import Decimal

from app.financial_engine.savings_calculator import (
    CategoryRemainderInput,
    automatic_savings,
    final_savings,
    manual_savings_total,
    undistributed_savings,
)


def test_automatic_savings_sums_only_positive_eligible_remainders():
    remainders = [
        CategoryRemainderInput(remaining=Decimal("500"), contributes_to_automatic_savings=True),
        CategoryRemainderInput(remaining=Decimal("400"), contributes_to_automatic_savings=True),
        CategoryRemainderInput(remaining=Decimal("400"), contributes_to_automatic_savings=True),
    ]
    assert automatic_savings(remainders) == Decimal("1300.0000")


def test_automatic_savings_excludes_ineligible_categories():
    remainders = [
        CategoryRemainderInput(remaining=Decimal("500"), contributes_to_automatic_savings=True),
        CategoryRemainderInput(remaining=Decimal("999"), contributes_to_automatic_savings=False),
    ]
    assert automatic_savings(remainders) == Decimal("500.0000")


def test_automatic_savings_never_subtracts_negative_remainders():
    """D-001: overspend (negative remainder) is never subtracted from automatic savings, even
    for an eligible category — only positive remainders are summed."""
    remainders = [
        CategoryRemainderInput(remaining=Decimal("500"), contributes_to_automatic_savings=True),
        CategoryRemainderInput(remaining=Decimal("-200"), contributes_to_automatic_savings=True),
    ]
    assert automatic_savings(remainders) == Decimal("500.0000")


def test_automatic_savings_zero_when_no_remainders():
    assert automatic_savings([]) == Decimal("0.0000")


def test_manual_savings_total_sums_items():
    assert manual_savings_total([Decimal("200"), Decimal("100")]) == Decimal("300.0000")


def test_final_savings_adds_automatic_and_manual():
    assert final_savings(Decimal("1300"), Decimal("0")) == Decimal("1300.0000")


def test_undistributed_savings_subtracts_distributed_from_final():
    assert undistributed_savings(Decimal("1300"), Decimal("1300")) == Decimal("0.0000")


def test_undistributed_savings_when_nothing_distributed_yet():
    assert undistributed_savings(Decimal("1300"), Decimal("0")) == Decimal("1300.0000")
