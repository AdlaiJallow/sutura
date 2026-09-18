"""Unit tests for distribution formulas (CLAUDE.md / spec §26, §12, §13)."""
from decimal import Decimal

from app.financial_engine.distribution_calculator import (
    category_allocation,
    category_remaining,
    category_used,
    compute_category_distribution,
    is_overspent,
)


def test_category_allocation_applies_percentage():
    result = category_allocation(Decimal("14000"), Decimal("50.00"))
    assert result == Decimal("7000.0000")


def test_category_used_sums_items():
    assert category_used([Decimal("100"), Decimal("50")]) == Decimal("150.0000")


def test_category_remaining_positive_when_under_budget():
    remaining = category_remaining(Decimal("7000"), Decimal("6500"))
    assert remaining == Decimal("500.0000")
    assert is_overspent(remaining) is False


def test_category_remaining_negative_on_overspend_is_visible_not_hidden():
    """Edge case §38: overspending shows a visible negative remaining balance; it never
    silently steals from another category (spec §13)."""
    remaining = category_remaining(Decimal("1000"), Decimal("1200"))
    assert remaining == Decimal("-200.0000")
    assert is_overspent(remaining) is True


def test_category_fully_unused_remaining_equals_full_allocation():
    """Edge case §38: a category that is never spent from at all."""
    remaining = category_remaining(category_allocation(Decimal("10000"), Decimal("20.00")), Decimal("0"))
    assert remaining == Decimal("2000.0000")


def test_compute_category_distribution_end_to_end():
    result = compute_category_distribution(
        category_id="needs",
        total_monthly_income=Decimal("14000"),
        percentage=Decimal("50.00"),
        item_amounts=[Decimal("6500")],
        contributes_to_automatic_savings=True,
    )
    assert result.allocation == Decimal("7000.0000")
    assert result.used == Decimal("6500.0000")
    assert result.remaining == Decimal("500.0000")
    assert result.is_overspent is False
