"""Unit test for the MonthlyFinancialSummary assembly (spec §22/§23)."""
from decimal import Decimal

from app.financial_engine.monthly_summary_calculator import MonthlySummaryInputs, build_monthly_summary


def test_build_monthly_summary_matches_worked_example():
    inputs = MonthlySummaryInputs(
        net_salary=Decimal("10000"),
        total_allowances=Decimal("3000"),
        total_other_income=Decimal("1000"),
        total_expenses=Decimal("12700"),
        total_planned_savings=Decimal("2800"),
        automatic_savings=Decimal("1300"),
        manual_savings=Decimal("0"),
        total_bank_deposits=Decimal("1300"),
        distributed_savings=Decimal("1300"),
    )
    result = build_monthly_summary(inputs)

    assert result.total_salary_income == Decimal("13000.0000")
    assert result.total_monthly_income == Decimal("14000.0000")
    assert result.final_savings == Decimal("1300.0000")
    assert result.undistributed_savings == Decimal("0.0000")


def test_build_monthly_summary_zero_income_edge_case():
    """Edge case §38: zero income — no exception, every figure is exactly zero."""
    inputs = MonthlySummaryInputs(
        net_salary=Decimal("0"),
        total_allowances=Decimal("0"),
        total_other_income=Decimal("0"),
        total_expenses=Decimal("0"),
        total_planned_savings=Decimal("0"),
        automatic_savings=Decimal("0"),
        manual_savings=Decimal("0"),
        total_bank_deposits=Decimal("0"),
        distributed_savings=Decimal("0"),
    )
    result = build_monthly_summary(inputs)

    assert result.total_monthly_income == Decimal("0.0000")
    assert result.final_savings == Decimal("0.0000")
    assert result.undistributed_savings == Decimal("0.0000")
