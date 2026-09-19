import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardView } from "./dashboard-view";
import type { BankAccountSummary, FinancialPeriod, MonthlySummary, SavingsSummary } from "@/lib/types";

const zeroPeriod: FinancialPeriod = {
  id: "period-zero",
  year: 2026,
  month: 9,
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  status: "OPEN",
  distribution_rule_id: null,
  base_currency: "GMD",
  closed_at: null,
  closed_by: null,
  reopened_count: 0,
  last_reopened_at: null,
};

const zeroSummary: MonthlySummary = {
  id: "summary-zero",
  financial_period_id: "period-zero",
  version: 0,
  is_current: true,
  total_salary_income: "0.0000",
  total_allowances: "0.0000",
  total_other_income: "0.0000",
  total_monthly_income: "0.0000",
  total_expenses: "0.0000",
  total_planned_savings: "0.0000",
  automatic_savings: "0.0000",
  manual_savings: "0.0000",
  final_savings: "0.0000",
  total_bank_deposits: "0.0000",
  undistributed_savings: "0.0000",
  triggered_by: "MANUAL_REFRESH",
  calculated_at: "2026-09-19T00:00:00Z",
};

const zeroSavings: SavingsSummary = {
  financial_period_id: "period-zero",
  automatic_savings_computed: "0.0000",
  manual_savings_total: "0.0000",
  final_savings_total: "0.0000",
  distributed_total: "0.0000",
  undistributed_total: "0.0000",
  last_calculated_at: null,
};

const noAccounts: BankAccountSummary[] = [];

describe("<DashboardView /> — zero income edge case (spec §38)", () => {
  it("renders the zero-income empty state instead of crashing or showing blank sections", () => {
    render(
      <DashboardView period={zeroPeriod} summary={zeroSummary} savings={zeroSavings} accounts={noAccounts} />,
    );

    expect(screen.getByText(/Nothing recorded for/i)).toBeInTheDocument();

    // It still tells the person what to do next rather than leaving a blank page.
    expect(screen.getByRole("link", { name: /add salary/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /add other income/i })).toBeInTheDocument();

    // No accounts recorded either — the accounts section should say so plainly.
    expect(screen.getByText(/no accounts added yet/i)).toBeInTheDocument();
  });

  it("shows a shortfall warning when undistributed savings goes negative (D-023) rather than hiding it", () => {
    const summary: MonthlySummary = {
      ...zeroSummary,
      total_salary_income: "38500.0000",
      total_monthly_income: "38500.0000",
    };
    const savings: SavingsSummary = {
      ...zeroSavings,
      final_savings_total: "100.0000",
      distributed_total: "200.0000",
      undistributed_total: "-100.0000",
    };

    render(<DashboardView period={zeroPeriod} summary={summary} savings={savings} accounts={noAccounts} />);

    expect(screen.getByText(/-GMD 100\.00/)).toBeInTheDocument();
    expect(screen.getByText(/more has been sent to accounts than your current savings cover/i)).toBeInTheDocument();
  });
});
