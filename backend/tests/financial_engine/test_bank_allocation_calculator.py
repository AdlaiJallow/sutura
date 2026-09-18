"""Unit tests for bank/savings allocation formulas (spec §19/§20, D-014)."""
from decimal import Decimal

from app.financial_engine.bank_allocation_calculator import (
    RuleItemInput,
    apply_percentage_rule,
    would_exceed_available,
)


def test_would_exceed_available_true_when_over_final_savings():
    assert would_exceed_available(
        already_allocated=Decimal("1000"), new_amount=Decimal("500"), final_savings_total=Decimal("1300")
    ) is True


def test_would_exceed_available_false_when_within_final_savings():
    assert would_exceed_available(
        already_allocated=Decimal("700"), new_amount=Decimal("600"), final_savings_total=Decimal("1300")
    ) is False


def test_apply_percentage_rule_splits_exactly_the_worked_example():
    results = apply_percentage_rule(
        amount_to_distribute=Decimal("1300"),
        rule_items=[
            RuleItemInput(key="bank_a", percentage=Decimal("54.00")),
            RuleItemInput(key="bank_b", percentage=Decimal("31.00")),
            RuleItemInput(key="emergency_fund", percentage=Decimal("15.00")),
        ],
    )
    total = sum((r.amount for r in results), Decimal("0"))
    assert total == Decimal("1300.0000")


def test_apply_percentage_rule_last_item_absorbs_rounding_residual():
    """Splitting an amount that doesn't divide evenly must never over- or under-allocate due to
    rounding drift (spec's rounding edge case, §38)."""
    results = apply_percentage_rule(
        amount_to_distribute=Decimal("100.00"),
        rule_items=[
            RuleItemInput(key="a", percentage=Decimal("33.33")),
            RuleItemInput(key="b", percentage=Decimal("33.33")),
            RuleItemInput(key="c", percentage=Decimal("33.34")),
        ],
    )
    total = sum((r.amount for r in results), Decimal("0"))
    assert total == Decimal("100.0000")
