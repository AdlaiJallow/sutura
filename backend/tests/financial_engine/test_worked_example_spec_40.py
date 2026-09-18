"""Reproduces the exact worked example from spec §40, end to end through financial_engine.

    D10,000 salary + D2,000 + D1,000 allowances + D500 + D500 other income -> D14,000 total
    -> 50/30/20 category split -> D6,500 / D3,900 / D2,300 spend
    -> D1,300 automatic savings -> D700 / D400 / D200 bank split -> D0 undistributed

This is the independent reproduction of the spec's worked example required by CLAUDE.md's
Definition of Done / spec §49.
"""
from decimal import Decimal

from app.financial_engine.bank_allocation_calculator import would_exceed_available
from app.financial_engine.distribution_calculator import category_allocation, category_remaining, category_used
from app.financial_engine.income_calculator import (
    total_allowances,
    total_monthly_income,
    total_other_income,
    total_salary_income,
)
from app.financial_engine.savings_calculator import (
    CategoryRemainderInput,
    automatic_savings,
    final_savings,
    manual_savings_total,
    undistributed_savings,
)


def test_worked_example_end_to_end():
    # --- Income ---
    net_salary = Decimal("10000")
    allowances_total = total_allowances([Decimal("2000"), Decimal("1000")])
    assert allowances_total == Decimal("3000.0000")

    salary_income = total_salary_income(net_salary, allowances_total)
    assert salary_income == Decimal("13000.0000")

    other_income_total = total_other_income([Decimal("500"), Decimal("500")])
    assert other_income_total == Decimal("1000.0000")

    monthly_income = total_monthly_income(salary_income, other_income_total)
    assert monthly_income == Decimal("14000.0000")

    # --- 50/30/20 distribution, all three categories eligible for automatic savings ---
    needs_allocation = category_allocation(monthly_income, Decimal("50.00"))
    wants_allocation = category_allocation(monthly_income, Decimal("30.00"))
    savings_bucket_allocation = category_allocation(monthly_income, Decimal("20.00"))
    assert needs_allocation == Decimal("7000.0000")
    assert wants_allocation == Decimal("4200.0000")
    assert savings_bucket_allocation == Decimal("2800.0000")

    needs_used = category_used([Decimal("6500")])
    wants_used = category_used([Decimal("3900")])
    savings_bucket_used = category_used([Decimal("2300")])

    needs_remaining = category_remaining(needs_allocation, needs_used)
    wants_remaining = category_remaining(wants_allocation, wants_used)
    savings_bucket_remaining = category_remaining(savings_bucket_allocation, savings_bucket_used)
    assert needs_remaining == Decimal("500.0000")
    assert wants_remaining == Decimal("300.0000")
    assert savings_bucket_remaining == Decimal("500.0000")

    # --- Automatic savings = sum of eligible positive remainders ---
    automatic = automatic_savings(
        [
            CategoryRemainderInput(remaining=needs_remaining, contributes_to_automatic_savings=True),
            CategoryRemainderInput(remaining=wants_remaining, contributes_to_automatic_savings=True),
            CategoryRemainderInput(
                remaining=savings_bucket_remaining, contributes_to_automatic_savings=True
            ),
        ]
    )
    assert automatic == Decimal("1300.0000")

    # --- No manual savings this month ---
    manual = manual_savings_total([])
    assert manual == Decimal("0.0000")

    final = final_savings(automatic, manual)
    assert final == Decimal("1300.0000")

    # --- Bank split: D700 / D400 / D200 == exactly Final Savings, never over-allocated ---
    bank_allocations = [Decimal("700"), Decimal("400"), Decimal("200")]
    distributed = sum(bank_allocations, Decimal("0"))
    assert distributed == Decimal("1300")
    assert would_exceed_available(
        already_allocated=Decimal("0"), new_amount=distributed, final_savings_total=final
    ) is False

    undistributed = undistributed_savings(final, distributed)
    assert undistributed == Decimal("0.0000")
