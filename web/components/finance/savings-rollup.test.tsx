import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SavingsRollup } from "./savings-rollup";
import type { SavingsSummary } from "@/lib/types";

afterEach(cleanup);

describe("<SavingsRollup /> — normal case", () => {
  it("renders every figure straight from the API and hides the undistributed callout at zero", () => {
    const summary: SavingsSummary = {
      financial_period_id: "period-1",
      automatic_savings_computed: "1500.0000",
      manual_savings_total: "500.0000",
      final_savings_total: "2000.0000",
      distributed_total: "2000.0000",
      undistributed_total: "0.0000",
      last_calculated_at: "2026-09-19T00:00:00Z",
    };

    render(<SavingsRollup summary={summary} currency="GMD" />);

    expect(screen.getByText("GMD 1,500.00")).toBeInTheDocument();
    expect(screen.getByText("GMD 500.00")).toBeInTheDocument();
    expect(screen.getAllByText("GMD 2,000.00").length).toBeGreaterThan(0);
    expect(screen.queryByText(/hasn't been sent/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/more has been sent/i)).not.toBeInTheDocument();
  });
});

describe("<SavingsRollup /> — negative undistributed (D-023, spec §38)", () => {
  it("shows a shortfall plainly, in the overspent tone, never clamped to zero", () => {
    const summary: SavingsSummary = {
      financial_period_id: "period-1",
      automatic_savings_computed: "1000.0000",
      manual_savings_total: "0.0000",
      final_savings_total: "1000.0000",
      distributed_total: "1300.0000",
      undistributed_total: "-300.0000",
      last_calculated_at: "2026-09-19T00:00:00Z",
    };

    render(<SavingsRollup summary={summary} currency="GMD" />);

    expect(screen.getByText("-GMD 300.00")).toBeInTheDocument();
    expect(screen.getByText(/more has been sent to accounts than your current savings cover/i)).toBeInTheDocument();
  });
});

describe("<SavingsRollup /> — positive undistributed", () => {
  it("prompts assigning the leftover instead of hiding it", () => {
    const summary: SavingsSummary = {
      financial_period_id: "period-1",
      automatic_savings_computed: "800.0000",
      manual_savings_total: "0.0000",
      final_savings_total: "800.0000",
      distributed_total: "500.0000",
      undistributed_total: "300.0000",
      last_calculated_at: "2026-09-19T00:00:00Z",
    };

    render(<SavingsRollup summary={summary} currency="GMD" />);

    expect(screen.getByText("GMD 300.00")).toBeInTheDocument();
    expect(screen.getByText(/hasn't been sent to an account or destination yet/i)).toBeInTheDocument();
  });
});
