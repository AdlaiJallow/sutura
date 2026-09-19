import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MonthlySummaryReport } from "./monthly-summary-report";
import type { FinancialPeriod, MonthlySummary } from "@/lib/types";

afterEach(cleanup);

const openPeriod: FinancialPeriod = {
  id: "period-sep-2026",
  year: 2026,
  month: 9,
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  status: "OPEN",
  distribution_rule_id: "rule-1",
  base_currency: "GMD",
  closed_at: null,
  closed_by: null,
  reopened_count: 0,
  last_reopened_at: null,
};

// Realistic figures: a salaried civil servant with allowances, some freelance
// income, an overspent month whose savings couldn't fully cover what was sent
// to accounts (undistributed_savings negative — spec §38/D-023).
const realSummary: MonthlySummary = {
  id: "summary-1",
  financial_period_id: "period-sep-2026",
  version: 3,
  is_current: true,
  total_salary_income: "42250.0000",
  total_allowances: "3750.0000",
  total_other_income: "6000.0000",
  total_monthly_income: "48250.0000",
  total_expenses: "31400.5000",
  total_planned_savings: "9000.0000",
  automatic_savings: "5200.0000",
  manual_savings: "1000.0000",
  final_savings: "6200.0000",
  total_bank_deposits: "6500.0000",
  undistributed_savings: "-300.0000",
  triggered_by: "MANUAL_REFRESH",
  calculated_at: "2026-09-19T14:32:00Z",
};

const zeroSummary: MonthlySummary = {
  ...realSummary,
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
};

describe("<MonthlySummaryReport /> — renders the backend's numbers exactly", () => {
  it("shows the period label and every figure from the summary, unmodified", () => {
    render(<MonthlySummaryReport period={openPeriod} summary={realSummary} />);

    expect(screen.getByText("September 2026")).toBeInTheDocument();
    expect(screen.getByText("GMD 48,250.00")).toBeInTheDocument(); // total monthly income
    expect(screen.getByText("GMD 31,400.50")).toBeInTheDocument(); // spent this period
    expect(screen.getByText("GMD 6,200.00")).toBeInTheDocument(); // final savings
  });

  it("shows a negative undistributed savings figure plainly, never clamped to zero", () => {
    render(<MonthlySummaryReport period={openPeriod} summary={realSummary} />);

    expect(screen.getByText("-GMD 300.00")).toBeInTheDocument();
    expect(screen.getByText(/more has been sent to accounts than/i)).toBeInTheDocument();
  });

  it("notes when a period is closed and the numbers are frozen, not live", () => {
    render(<MonthlySummaryReport period={{ ...openPeriod, status: "CLOSED" }} summary={realSummary} />);
    expect(screen.getByText(/Frozen at the numbers/i)).toBeInTheDocument();
  });

  it("flags a zero-income period honestly instead of showing a blank or broken layout", () => {
    render(<MonthlySummaryReport period={openPeriod} summary={zeroSummary} />);

    expect(screen.getByText(/No income has been recorded/i)).toBeInTheDocument();
    expect(screen.getAllByText("GMD 0.00").length).toBeGreaterThan(0);
  });
});
