import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { PeriodDistributionView } from "./period-distribution-view";
import type { DistributionRule, DistributionView, FinancialPeriod } from "@/lib/types";

afterEach(cleanup);

const openPeriod: FinancialPeriod = {
  id: "period-1",
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

const rules: DistributionRule[] = [
  {
    id: "rule-1",
    name: "My 50/30/20",
    description: null,
    is_active: true,
    is_default: true,
    categories: [],
    updated_at: "2026-09-01T00:00:00Z",
  },
];

function baseProps() {
  return {
    period: openPeriod,
    error: null,
    loading: false,
    onReload: vi.fn(),
    rules,
    rulesError: null,
    onRuleApplied: vi.fn(),
    onCreateRule: vi.fn(),
  };
}

describe("<PeriodDistributionView /> — normal, on-track case", () => {
  it("renders every category's allocation/used/remaining straight from the API, with no overspent flag", () => {
    const view: DistributionView = {
      financial_period_id: "period-1",
      distribution_rule_id: "rule-1",
      distribution_rule_name: "My 50/30/20",
      total_monthly_income: "20000.0000",
      total_allocation: "20000.0000",
      total_used: "6000.0000",
      total_remaining: "14000.0000",
      categories: [
        {
          id: "cat-needs",
          name: "Needs",
          percentage: "50.00",
          allocation: "10000.0000",
          used: "6000.0000",
          remaining: "4000.0000",
          is_overspent: false,
          contributes_to_automatic_savings: false,
          is_unallocated_bucket: false,
        },
        {
          id: "cat-savings",
          name: "Savings",
          percentage: "20.00",
          allocation: "4000.0000",
          used: "0.0000",
          remaining: "4000.0000",
          is_overspent: false,
          contributes_to_automatic_savings: true,
          is_unallocated_bucket: false,
        },
      ],
    };

    render(<PeriodDistributionView {...baseProps()} view={view} />);

    // "My 50/30/20" also appears inside the rule-switcher select — assert on
    // the "Active rule" heading's own value specifically.
    expect(screen.getByText("Active rule").nextElementSibling).toHaveTextContent("My 50/30/20");
    expect(screen.getByText("Needs")).toBeInTheDocument();
    expect(screen.getByText("Savings")).toBeInTheDocument();
    // Two "Remaining" figures: the period total and this category's own.
    expect(screen.getAllByText("GMD 4,000.00").length).toBeGreaterThan(0);
    expect(screen.queryByText(/overspent/i)).not.toBeInTheDocument();
  });
});

describe("<PeriodDistributionView /> — overspent case (spec §13/§38)", () => {
  it("shows the overspent category's negative remaining plainly, never hidden or clamped to zero", () => {
    const view: DistributionView = {
      financial_period_id: "period-1",
      distribution_rule_id: "rule-1",
      distribution_rule_name: "My 50/30/20",
      total_monthly_income: "20000.0000",
      total_allocation: "20000.0000",
      total_used: "12000.0000",
      total_remaining: "8000.0000",
      categories: [
        {
          id: "cat-needs",
          name: "Needs",
          percentage: "50.00",
          allocation: "10000.0000",
          used: "12000.0000",
          remaining: "-2000.0000",
          is_overspent: true,
          contributes_to_automatic_savings: false,
          is_unallocated_bucket: false,
        },
      ],
    };

    render(<PeriodDistributionView {...baseProps()} view={view} />);

    expect(screen.getByText("Overspent")).toBeInTheDocument();
    expect(screen.getByText("-GMD 2,000.00")).toBeInTheDocument();
  });
});

describe("<PeriodDistributionView /> — closed period (spec §5/§37)", () => {
  it("explains the rule can't be changed instead of offering the switch control", () => {
    const closedPeriod: FinancialPeriod = { ...openPeriod, status: "CLOSED" };
    const view: DistributionView = {
      financial_period_id: "period-1",
      distribution_rule_id: "rule-1",
      distribution_rule_name: "My 50/30/20",
      total_monthly_income: "20000.0000",
      total_allocation: "20000.0000",
      total_used: "6000.0000",
      total_remaining: "14000.0000",
      categories: [],
    };

    render(<PeriodDistributionView {...baseProps()} period={closedPeriod} view={view} />);

    expect(screen.getByText(/this period is closed/i)).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});

describe("<PeriodDistributionView /> — no rule selected yet (a normal 200, not an error)", () => {
  it("shows an empty state prompting the user to choose or create a rule instead of a blank page", () => {
    const view: DistributionView = {
      financial_period_id: "period-1",
      distribution_rule_id: null,
      distribution_rule_name: null,
      total_monthly_income: "0.0000",
      total_allocation: "0.0000",
      total_used: "0.0000",
      total_remaining: "0.0000",
      categories: [],
    };

    render(<PeriodDistributionView {...baseProps()} view={view} />);

    expect(screen.getByText("No distribution rule selected yet")).toBeInTheDocument();
  });

  it("offers to create a rule instead of a selector when the user has none yet", () => {
    const view: DistributionView = {
      financial_period_id: "period-1",
      distribution_rule_id: null,
      distribution_rule_name: null,
      total_monthly_income: "0.0000",
      total_allocation: "0.0000",
      total_used: "0.0000",
      total_remaining: "0.0000",
      categories: [],
    };

    render(<PeriodDistributionView {...baseProps()} view={view} rules={[]} />);

    expect(screen.getByRole("button", { name: "Create a distribution rule" })).toBeInTheDocument();
  });
});
